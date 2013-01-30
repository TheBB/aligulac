#!/usr/bin/python
import csv

with open('tlpd_out', 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')

    date = None
    pls = [None, None]
    sca, scb = 0, 0
    prevrow = None

    completed = []

    for row in reader:
        if date == row[1] and row[5] in pls and row[8] in pls:
            if row[5] == pls[0]:
                sca += 1
            else:
                scb += 1
        else:
            if prevrow != None:
                write = prevrow[1:4] + [prevrow[5]]
                if prevrow[5] == pls[0]:
                    write += [str(sca)]
                else:
                    write += [str(scb)]
                write += [prevrow[6], prevrow[8]]
                if prevrow[5] == pls[0]:
                    write += [str(scb)]
                else:
                    write += [str(sca)]
                completed += [write]

            date = row[1]
            pls = [row[5], row[8]]
            sca, scb = 1, 0

        prevrow = row

    write = prevrow[1:4] + [prevrow[5]]
    if prevrow[5] == pls[0]:
        write += [str(sca)]
    else:
        write += [str(scb)]
    write += [prevrow[6], prevrow[8]]
    if prevrow[5] == pls[0]:
        write += [str(scb)]
    else:
        write += [str(sca)]
    completed += [write]

with open('tlpd_international_proc', 'wb') as f:
    writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for r in completed:
        writer.writerow(r)
