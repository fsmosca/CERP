import chess
import chess.engine
import pandas as pd
import concurrent.futures
import os
import csv
import logging
from collections import defaultdict
import time
import argparse
import re


def setup_worker_logging(engine_name, worker_id):
    """Configures the chess.engine logger for a specific worker process."""
    uci_logger = logging.getLogger("chess.engine")

    if uci_logger.hasHandlers():
        uci_logger.handlers.clear()

    log_filename = f"{engine_name.replace(' ', '_')}_analysis_worker_{worker_id}.txt"

    uci_log_handler = logging.FileHandler(log_filename, mode="w")
    uci_log_handler.setLevel(logging.DEBUG)
    uci_log_handler.setFormatter(logging.Formatter('%(asctime)s - (PID:%(process)d) - %(message)s'))

    uci_logger.setLevel(logging.DEBUG)
    uci_logger.addHandler(uci_log_handler)


def create_chunks(data_list, num_chunks):
    """Splits a list into a specified number of nearly equal-sized chunks."""
    if not data_list: return []
    base_chunk_size, remainder = divmod(len(data_list), num_chunks)
    chunks, current_index = [], 0
    for i in range(num_chunks):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        chunks.append(data_list[current_index : current_index + chunk_size])
        current_index += chunk_size
    return chunks


def analyze_chunk(fen_chunk, worker_id, engine_name, engine_path, move_time, custom_options, enable_uci_log):
    """Worker function: Starts and configures an engine to analyze a chunk of FENs."""
    if enable_uci_log:
        setup_worker_logging(engine_name, worker_id)

    chunk_results = {}
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)

        # Configure any custom UCI options provided
        if custom_options:
            for option_str in custom_options:
                if "=" in option_str:
                    name, value = option_str.split("=", 1)
                    try:
                        engine.configure({name.strip(): value.strip()})
                    except Exception as e:
                        print(f"Worker {worker_id} Warning: Could not set option '{name}'. Engine says: {e}")
                else:
                    print(f"Worker {worker_id} Warning: Ignoring invalid option format '{option_str}'. Use Name=Value.")

        for fen in fen_chunk:
            board = chess.Board(fen)

            # game=object() forces the chess library to send ucinewgame command to the engine
            info = engine.analyse(board, chess.engine.Limit(time=move_time), game=object())
            if "pv" in info and info["pv"]:
                chunk_results[fen] = info["pv"][0].uci()
            else:
                chunk_results[fen] = None
    except Exception as e:
        if enable_uci_log:
            logging.getLogger("chess.engine").error(f"Error in worker process {worker_id}: {e}", exc_info=True)
    finally:
        if 'engine' in locals():
            engine.quit()
    return chunk_results


def parse_epd_file(filepath):
    """Reads an EPD file and parses it into a structured pandas DataFrame."""
    print(f"Parsing EPD file: {filepath}...")
    try:
        with open(filepath, 'r') as f:
            epd_lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Could not find the file '{filepath}'")
        return None

    dfs_list = []
    for epd in epd_lines:
        board = chess.Board()
        try:
            epd_info = board.set_epd(epd)
            df_data = {
                'uci_move': epd_info.get('c9', '').split(),
                'points': [int(p) for p in epd_info.get('c8', '0').split()],
                'fen': board.fen(),
                'id': epd_info.get('id', '')
            }
            dfs_list.append(pd.DataFrame(df_data))
        except (ValueError, KeyError):
            continue

    if not dfs_list:
        return None

    return pd.concat(dfs_list, ignore_index=True)


def run_analysis(fens_to_analyze, num_workers, engine_name, engine_path, move_time, custom_options, enable_uci_log):
    """Runs the engine analysis concurrently, passing settings to each worker."""
    fen_chunks = create_chunks(fens_to_analyze, num_workers)
    engine_moves = {}

    print(f"Starting analysis of {len(fens_to_analyze)} positions with {num_workers} workers...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_chunk = {}
        for worker_id, chunk in enumerate(fen_chunks, 1):
            future = executor.submit(
                analyze_chunk,
                chunk,
                worker_id,
                engine_name,
                engine_path,
                move_time,
                custom_options,
                enable_uci_log
            )
            future_to_chunk[future] = chunk

        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_result = future.result()
            engine_moves.update(chunk_result)

    print(f"\nAnalysis complete.")
    return engine_moves


def calculate_scores(engine_name, engine_moves, df):
    """Calculates scores and saves a sorted, detailed analysis to a CSV file."""
    epd_data_lookup = {}
    for fen, group in df.groupby('fen'):
        epd_data_lookup[fen] = {
            'id': group['id'].iloc[0],
            'scored_moves': list(zip(group['uci_move'], group['points']))
        }

    total_points = 0
    suite_scores = defaultdict(int)
    results_data, warnings_data = [], []

    for fen, engine_best_move in engine_moves.items():
        position_data = epd_data_lookup.get(fen)
        if not position_data:
            warnings_data.append([f'WARNING: FEN not found', fen, '', '', ''])
            continue

        position_id = position_data['id']
        scored_moves_list = position_data['scored_moves']
        awarded_points = 0
        for move, points in scored_moves_list:
            if move == engine_best_move:
                awarded_points = points
                break

        total_points += awarded_points
        suite_id = position_id.split(' ', 1)[0]
        suite_scores[suite_id] += awarded_points
        epd_moves_str = ", ".join([f"{move}={pts}" for move, pts in scored_moves_list])
        results_data.append([position_id, fen, engine_best_move, epd_moves_str, awarded_points])

    def version_sort_key(row):
        return [int(s) for s in re.findall(r'\d+', row[0])]

    results_data.sort(key=version_sort_key)

    details_csv_filename = f"{engine_name.replace(' ', '_')}_details.csv"
    with open(details_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['ID', 'FEN', 'EngineMove', 'EPDMoves', 'Points'])
        csv_writer.writerows(results_data)
        if warnings_data:
            csv_writer.writerows(warnings_data)

    print(f"Detailed analysis saved to '{details_csv_filename}'.")
    return total_points, suite_scores


def generate_reports(engine_name, move_time, total_points, suite_scores, df, epd_filepath):
    """Generates and saves the summary, strength, weakness, and overall CSV reports."""
    print("Generating reports...")

    id_parser_df = df[['id']].copy().drop_duplicates()
    id_parts = id_parser_df['id'].str.split(' ', n=1, expand=True)
    id_parser_df['SuiteId'] = id_parts[0]
    id_parser_df['Description'] = id_parts[1].str.replace(r'\.\d+$', '', regex=True) if id_parts.shape[1] > 1 else ''
    suite_desc_lookup = id_parser_df.set_index('SuiteId')['Description'].to_dict()
    id_df = df.drop_duplicates(subset=['id']).copy()
    id_df['Id'] = id_df['id'].str.split(' ', n=1).str[0]
    suite_totals = id_df.groupby('Id')['id'].count().multiply(100).to_dict()

    summary_data = [{'Id': suite, 'Points': score} for suite, score in suite_scores.items()]
    summary_df = pd.DataFrame(summary_data)
    summary_df['Engine'] = engine_name
    summary_df['MTS'] = move_time
    summary_df['Description'] = summary_df['Id'].map(suite_desc_lookup).fillna('')
    summary_df['Total'] = summary_df['Id'].map(suite_totals).fillna(0).astype(int)
    summary_df['Pct'] = summary_df.apply(lambda row: round((row['Points'] / row['Total']) * 100.0, 2) if row['Total'] > 0 else 0, axis=1)
    summary_df = summary_df.sort_values(by='Id', key=lambda id_series: id_series.str.extract(r'(\d+)')[0].astype(int)).reset_index(drop=True)
    summary_df = summary_df[['Engine', 'Id', 'Description', 'MTS', 'Points', 'Total', 'Pct']]
    summary_filename = f"{engine_name.replace(' ', '_')}_summary.csv"
    summary_df.to_csv(summary_filename, index=False)

    grand_total_possible = sum(suite_totals.values())
    overall_pct = round((total_points / grand_total_possible) * 100.0, 2) if grand_total_possible > 0 else 0

    overall_summary_csv = "points.csv"
    test_suite_filename = os.path.basename(epd_filepath)

    new_row_data = {
        'Engine': engine_name,
        'TFile': test_suite_filename,
        'MTS': move_time,
        'Points': total_points,
        'Total': grand_total_possible,
        'Pct': overall_pct
    }

    try:
        points_df = pd.read_csv(overall_summary_csv)
        new_row_df = pd.DataFrame([new_row_data])
        points_df = pd.concat([points_df, new_row_df], ignore_index=True)
    except FileNotFoundError:
        points_df = pd.DataFrame([new_row_data])

    points_df_sorted = points_df.sort_values(
        by=['TFile', 'MTS', 'Pct'],
        ascending=[True, True, False]
    ).reset_index(drop=True)

    points_df_sorted.to_csv(overall_summary_csv, index=False)

    report_df = summary_df.copy()
    report_df['TFile'] = test_suite_filename
    report_df = report_df.rename(columns={'Id': 'ID'})
    final_columns = ['Engine', 'TFile', 'ID', 'Description', 'Points', 'Total', 'Pct']
    report_df = report_df[final_columns]

    strength_df = report_df.sort_values(by='Pct', ascending=False).head(5)
    strength_filename = f"{engine_name.replace(' ', '_')}_strength.csv"
    strength_df.to_csv(strength_filename, index=False)

    weakness_df = report_df.sort_values(by='Pct', ascending=True).head(5)
    weakness_filename = f"{engine_name.replace(' ', '_')}_weakness.csv"
    weakness_df.to_csv(weakness_filename, index=False)

    print(f"\nEngine '{engine_name}' scored a total of {total_points} points.")
    print(f"Suite summary saved to '{summary_filename}'.")
    print(f"Strength report (top 5 by Pct) saved to '{strength_filename}'.")
    print(f"Weakness report (top 5 by Pct) saved to '{weakness_filename}'.")
    print(f"Overall results in '{overall_summary_csv}' have been updated and sorted.")


def main():
    """Main function to orchestrate the EPD analysis workflow."""
    parser = argparse.ArgumentParser(
        description="Run a chess engine against an EPD test suite and calculate its score.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("epd_file", help="Path to the EPD test suite file.")
    parser.add_argument("-p", "--engine-path", required=True, help="Path to the chess engine executable.")
    
    parser.add_argument("-n", "--engine-name",
                        help="Name of the engine for reports (if not provided, queries the engine).")

    parser.add_argument("-w", "--workers", type=int, default=1, help="Number of parallel engine processes (default: 1).")
    parser.add_argument("-mt", "--movetime", type=float, default=1.0, help="Analysis time in seconds per move (default: 1.0).")
    parser.add_argument("--uci-log", action="store_true", help="Enable detailed UCI communication logging to a file for each worker.")

    parser.add_argument("-o", "--option", action="append",
                        help="Set a custom UCI option for the engine.\n"
                             "Use the format 'Name=Value'. This argument can be repeated.\n"
                             "Example: -o Threads=4 -o Hash=128")

    args = parser.parse_args()

    if not args.engine_name:
        print("Engine name not provided, querying from engine executable...")
        engine = None
        try:
            engine = chess.engine.SimpleEngine.popen_uci(args.engine_path)
            args.engine_name = engine.id['name']
            print(f"--> Detected engine name: {args.engine_name}")
        except Exception as e:
            print(f"\nError: Could not query engine name from '{args.engine_path}'.")
            print("Please specify it manually using the -n or --engine-name argument.")
            print(f"Details: {e}")
            return
        finally:
            if engine:
                engine.quit()

    parsed_df = parse_epd_file(args.epd_file)
    if parsed_df is None:
        print("Failed to parse EPD file. Exiting.")
        return

    t0 = time.perf_counter()

    unique_fens = parsed_df['fen'].unique()
    analysis_results = run_analysis(
        fens_to_analyze=list(unique_fens),
        num_workers=args.workers,
        engine_name=args.engine_name,
        engine_path=args.engine_path,
        move_time=args.movetime,
        custom_options=args.option,
        enable_uci_log=args.uci_log
    )

    total_points, suite_scores = calculate_scores(args.engine_name, analysis_results, parsed_df)
    t1 = time.perf_counter()
    generate_reports(args.engine_name, args.movetime, total_points, suite_scores, parsed_df, args.epd_file)

    print(f'\nElapsed (sec): {round(t1-t0,0)}')

    if args.uci_log:
        engine_name_safe = args.engine_name.replace(' ', '_')
        print(f"Detailed engine communication saved to '{engine_name_safe}_analysis_worker_*.txt'.")


if __name__ == "__main__":
    main()
