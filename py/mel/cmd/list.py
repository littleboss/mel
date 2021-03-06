"""List the moles in a mole catalog."""

import datetime
import os


def setup_parser(parser):
    parser.add_argument(
        '--only-no-micro',
        action='store_true',
        help="Only list moles that have no microscope images.")

    assistance = parser.add_mutually_exclusive_group()
    assistance.add_argument(
        '--without-assistance',
        action='store_true',
        help="Only list moles that don't require assistance to capture.")
    assistance.add_argument(
        '--with-assistance',
        action='store_true',
        help="Only list moles that require assistance to capture.")

    parser.add_argument(
        '--format',
        default="{relpath}",
        help="Print the results with the specified format. Defaults to "
             "'{relpath}'. Available keys: relpath, lastmicro, "
             "lastmicro_age_days, id.")

    parser.add_argument(
        '--sort',
        choices=['lastmicro'])


def process_args(args):
    if args.sort == 'lastmicro':
        def keyfunc(x):
            if not x.micro_filenames:
                return str()
            return sorted(x.micro_filenames)[-1]
    else:
        def keyfunc(x):
            return 0

    now = datetime.datetime.now()

    for mole in sorted(_yield_mole_dirs('.', args), key=keyfunc):
        mole_data = {
            'relpath': mole.catalog_relative_path,
            'lastmicro': '',
            'lastmicro_age_days': '',
            'id': mole.id_,
        }
        if mole.micro_filenames:
            lastmicro = sorted(mole.micro_filenames)[-1]
            mole_data['lastmicro'] = lastmicro
            lastmicrodtstring = lastmicro.split('.', 1)[0]
            lastmicrodt = datetime.datetime.strptime(
                lastmicrodtstring, '%Y%m%dT%H%M%S')
            age = now - lastmicrodt
            mole_data['lastmicro_age_days'] = age.days

        print(args.format.format(**mole_data))


class _Mole():

    def __init__(self, catalog_relative_path, micro_filenames):
        self.catalog_relative_path = catalog_relative_path
        self.micro_filenames = micro_filenames
        self.id_ = None


def _yield_mole_dirs(rootpath, args):
    for path, dirs, files in os.walk(rootpath):

        this_dirname = os.path.basename(path)

        if this_dirname.startswith('__'):
            continue

        catalog_relpath = os.path.relpath(path, rootpath)

        # ignore directories with no files
        if not files:
            continue

        # ignore dot-directories in the root, like '.git'
        if catalog_relpath.startswith('.'):
            continue

        unknown_dirs = set(dirs)

        if args.only_no_micro and '__micro__' in unknown_dirs:
            if os.listdir(os.path.join(path, '__micro__')):
                continue

        if args.without_assistance and '__need_assistance__' in files:
            continue

        if args.with_assistance and '__need_assistance__' not in files:
            continue

        micro_filenames = []
        if '__micro__' in unknown_dirs:
            micro_filenames = os.listdir(os.path.join(path, '__micro__'))

        discard_dirs = set(x for x in unknown_dirs if x.startswith('__'))
        unknown_dirs -= discard_dirs

        # mole clusters have a picture and all the moles as child dirs, ignore
        if unknown_dirs:
            continue

        mole = _Mole(catalog_relpath, micro_filenames)

        if '__id__' in files:
            with open(os.path.join(path, '__id__')) as f:
                mole.id_ = f.read().strip()

        yield mole
