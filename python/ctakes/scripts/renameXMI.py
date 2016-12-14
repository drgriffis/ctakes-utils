'''
Renames cTAKES XMI output files (named like doc%d.xmi) to use the original document name.

E.g. Plaintext abc.txt -> cTAKES doc0.xmi -> renamed abc.xmi
'''

import os
from ctakes.format import XMI

if __name__ == '__main__':
    def _cli():
        import optparse
        parser = optparse.OptionParser(usage='Usage: %prog XMIDIR')
        (options, args) = parser.parse_args()
        if len(args) != 1:
            parser.print_help()
            exit()
        (xmidir,) = args
        return xmidir

    xmidir = _cli()

    print("Renaming files in %s..." % xmidir)
    for f in os.listdir(xmidir):
        if os.path.splitext(f)[1] == '.xmi':
            path = os.path.join(xmidir, f)
            docID = XMI.getDocumentID(path)
            new_path = os.path.join(xmidir, '%s.xmi' % os.path.splitext(docID)[0])
            if not os.path.isfile(new_path):
                os.rename(path, new_path)
                print("  >> Renamed %s to %s" % (path, new_path))
            elif path != new_path:
                print("[NAME COLLISION] File %s already exists (skipping %s)" % (new_path, path))
