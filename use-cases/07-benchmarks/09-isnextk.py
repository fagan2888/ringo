import os
import resource
import sys
import time

sys.path.append("../utils")

import snap
import testutils

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print """Usage: """ + sys.argv[0] + """ <srcfile>
        srcfile: posts.tsv file from StackOverflow dataset"""
        sys.exit(1)

    srcfile = sys.argv[1]

    context = snap.TTableContext()

    t = testutils.Timer()
    r = testutils.Resource()

    schema = snap.Schema()
    schema.Add(snap.TStrTAttrPr("Id", snap.atInt))
    schema.Add(snap.TStrTAttrPr("OwnerUserId", snap.atInt))
    schema.Add(snap.TStrTAttrPr("AcceptedAnswerId", snap.atInt))
    schema.Add(snap.TStrTAttrPr("CreationDate", snap.atStr))
    schema.Add(snap.TStrTAttrPr("Score", snap.atInt))
    table = snap.TTable.LoadSS("1", schema, srcfile, context, "\t", snap.TBool(False))
    t.show("load text", table)
    r.show("__loadtext__")

    table = table.IsNextK("CreationDate", 1, "OwnerUserId")
    t.show("isnextk", table)
    r.show("__isnextk__")

