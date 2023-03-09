import argparse
from pathlib import Path
import inspect
import json

import ghidriff
from ghidriff import GhidraDiffEngine


def main():
    """
    ghidriff - GhidraDiffEngine module main function
    """

    # setup engines
    engines = {}
    for name, klass in inspect.getmembers(ghidriff, inspect.isclass):
        if name.endswith('Diff'):
            engines[name] = klass

    parser = argparse.ArgumentParser(description='ghidriff - A Command Line Ghidra Binary Diffing Engine',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('old', nargs=1, help="Path to old version of binary '/somewhere/bin.old'")
    parser.add_argument('new', action='append', nargs='+',
                        help="Path to new version of binary '/somewhere/bin.new'. (For multiple new binaries add oldest to newest)")
    parser.add_argument('--engine', help='The diff implementation to use.',
                        default='VersionTrackingDiff', choices=engines.keys())
    parser.add_argument('-o', '--output-path', help='Output path for resulting diffs', default='.ghidriffs')

    GhidraDiffEngine.add_ghidra_args_to_parser(parser)

    args = parser.parse_args()

    output_path = Path(args.output_path)
    output_path.mkdir(exist_ok=True)

    if args.log_path == parser.get_default('log_path'):
        engine_log_path = output_path / parser.get_default('log_path')
    else:
        engine_log_path = Path(args.log_path)

    binary_paths = args.old + [bin for sublist in args.new for bin in sublist]

    binary_paths = [Path(path) for path in binary_paths]

    project_name = f'{args.project_name}-{binary_paths[0].name}-{binary_paths[-1].name}'

    DiffEngine: GhidraDiffEngine = engines[args.engine]

    d: GhidraDiffEngine = DiffEngine(args=args,
                                     verbose=True,
                                     threaded=args.threaded,
                                     max_ram_percent=args.max_ram_percent,
                                     print_jvm_flags=args.print_flags,
                                     jvm_args=args.jvm_args,
                                     force_analysis=args.force_analysis,
                                     force_diff=args.force_diff,
                                     engine_log_path=engine_log_path,
                                     engine_log_level=args.log_level,
                                     engine_file_log_level=args.file_log_level
                                     )

    d.setup_project(binary_paths, args.project_location, project_name, args.symbols_path)

    d.analyze_project()

    diffs = []

    # pair up binaries with the n-1 version
    for i in range(len(binary_paths)-1):
        diffs.append((binary_paths[i], binary_paths[i+1]))

    # add a diff of the first and last binary for full coverage
    if not binary_paths[1] == binary_paths[-1]:
        diffs.append((binary_paths[0], binary_paths[-1]))

    for diff in diffs:
        pdiff = d.diff_bins(diff[0], diff[1])
        pdiff_json = json.dumps(pdiff)

        d.validate_diff_json(pdiff_json)

        diff_name = f"{Path(diff[0]).name}-{Path(diff[1]).name}_diff"

        d.dump_pdiff_to_dir(diff_name,
                            pdiff,
                            output_path,
                            side_by_side=args.side_by_side,
                            max_section_funcs=args.max_section_funcs)


if __name__ == "__main__":
    main()
