"""
Parse test jobs and dependencies YAML for GDASApp GW-CI tests.

Generates CMake commands from the YAML configuration file.

Usage (tasks mode):
    parse_deps.py <yaml_file> <pslot> --mode tasks
    Outputs CMake set() commands for HALF_CYCLE_TASKS and FULL_CYCLE_TASKS.

Usage (deps mode):
    parse_deps.py <yaml_file> <pslot> --mode deps --half-date <date> --full-date <date>
    Outputs CMake set_tests_properties() commands for test dependencies.

Dependency notation in the YAML:
    H:<task>  - depends on the named task from the half cycle
    F:<task>  - depends on the named task from the full cycle
Tasks with no dependency entry depend on the experiment setup test (create_exp).
"""

import sys
import argparse
import yaml


def expand_dep(dep, prefix, half_date, full_date):
    """Expand a H: or F: dependency notation to a full CMake test name."""
    if dep.startswith('H:'):
        return f"{prefix}_{dep[2:]}_{half_date}"
    elif dep.startswith('F:'):
        return f"{prefix}_{dep[2:]}_{full_date}"
    else:
        raise ValueError(f"Unknown dependency prefix in '{dep}': expected 'H:' or 'F:'")


def print_tasks(data, pslot):
    """Output CMake set() commands for the half- and full-cycle task lists."""
    if pslot not in data:
        print(f"# Warning: pslot '{pslot}' not found in {sys.argv[1]}", file=sys.stderr)
        print("set(HALF_CYCLE_TASKS)")
        print("set(FULL_CYCLE_TASKS)")
        return

    pslot_data = data[pslot]
    half_tasks = pslot_data.get('half_cycle', {}).get('tasks', [])
    full_tasks = pslot_data.get('full_cycle', {}).get('tasks', [])

    if half_tasks:
        tasks_joined = '\n  '.join(half_tasks)
        print(f"set(HALF_CYCLE_TASKS\n  {tasks_joined})")
    else:
        print("set(HALF_CYCLE_TASKS)")

    if full_tasks:
        tasks_joined = '\n  '.join(full_tasks)
        print(f"set(FULL_CYCLE_TASKS\n  {tasks_joined})")
    else:
        print("set(FULL_CYCLE_TASKS)")


def print_deps(data, pslot, half_date, full_date):
    """Output CMake set_tests_properties() commands for all test dependencies."""
    if pslot not in data:
        print(f"# Warning: pslot '{pslot}' not found in {sys.argv[1]}", file=sys.stderr)
        return

    prefix = f"test_gdasapp_{pslot}"
    create_exp = prefix  # experiment setup test has no cycle date suffix

    pslot_data = data[pslot]

    # Half-cycle tasks
    half_cycle = pslot_data.get('half_cycle', {})
    half_tasks = half_cycle.get('tasks', [])
    half_deps_map = half_cycle.get('dependencies', {})

    for task in half_tasks:
        test_name = f"{prefix}_{task}_{half_date}"
        if task in half_deps_map:
            deps = [expand_dep(d, prefix, half_date, full_date) for d in half_deps_map[task]]
            deps_str = ';'.join(deps)
        else:
            deps_str = create_exp
        print(f'set_tests_properties({test_name} PROPERTIES DEPENDS "{deps_str}")')

    # Full-cycle tasks
    full_cycle = pslot_data.get('full_cycle', {})
    full_tasks = full_cycle.get('tasks', [])
    full_deps_map = full_cycle.get('dependencies', {})

    for task in full_tasks:
        test_name = f"{prefix}_{task}_{full_date}"
        if task in full_deps_map:
            deps = [expand_dep(d, prefix, half_date, full_date) for d in full_deps_map[task]]
            deps_str = ';'.join(deps)
        else:
            deps_str = create_exp
        print(f'set_tests_properties({test_name} PROPERTIES DEPENDS "{deps_str}")')


def main():
    parser = argparse.ArgumentParser(
        description="Parse GDASApp GW-CI test jobs and dependencies YAML.")
    parser.add_argument('yaml_file', help="Path to test_jobs_deps.yaml")
    parser.add_argument('pslot', help="Pslot (CI case) name")
    parser.add_argument('--mode', choices=['tasks', 'deps'], required=True,
                        help="Output mode: 'tasks' outputs task lists, 'deps' outputs dependencies")
    parser.add_argument('--half-date', dest='half_date',
                        help="Half-cycle date string (required for deps mode)")
    parser.add_argument('--full-date', dest='full_date',
                        help="Full-cycle date string (required for deps mode)")
    args = parser.parse_args()

    with open(args.yaml_file, 'r') as fh:
        data = yaml.safe_load(fh)

    if args.mode == 'tasks':
        print_tasks(data, args.pslot)
    else:  # deps
        if not args.half_date or not args.full_date:
            print("Error: --half-date and --full-date are required for deps mode", file=sys.stderr)
            sys.exit(1)
        print_deps(data, args.pslot, args.half_date, args.full_date)


if __name__ == "__main__":
    main()
