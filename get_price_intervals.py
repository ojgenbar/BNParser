#!/usr/bin/env python
# coding: UTF-8
import cPickle
import math


def get_price_intervals(prices, step, start, stop, quantity):

    gist_dict = {}

    for price in prices:
        k = int(round(price/step))
        gist_dict[k] = gist_dict.get(k, 0) + 1

    intervals = []
    elems = sorted(gist_dict.items())
    curq = 0
    curstart = start
    for k, v in elems:
        if curq + v <= quantity:
            curq += v
        else:
            intervals.append([curstart*step, k*step - step, curq])
            curstart = k
            curq = v
    intervals.append((curstart, stop, curq))

    # print sorted(gist_dict.items())[:10]
    # for start, stop, q in intervals:
    #     print start, stop, stop-start, q
    print 'Total price intervals:', len(intervals)
    return intervals


def intervals_from_list(properties_list, outpath,  step, start, stop, quantity):
    prices = [i[13] for i in properties_list]
    interv = get_price_intervals(prices, step, start, stop, quantity)
    out = ''
    for row in interv:
        out += '\t'.join([str(i) for i in row]) + '\n'
    open(outpath, 'w').write(out)
    return out


def intervals_from_file(inpath, outpath,  step, start, stop, quantity):

    dump = cPickle.load(open(inpath, 'rb'))
    out = intervals_from_list(
        properties_list=dump,
        outpath=outpath,
        step=step,
        start=start,
        stop=stop,
        quantity=quantity
    )
    return out


if __name__ == "__main__":
    outs = intervals_from_file(
        inpath=r'D:\Google Drive\BNParserData\2017.10.24_22.47\parsed\BNp2_list.pd',
        outpath=r'D:\OneDrive\Programs for Everything\RealEstate_project\BNParser\BNp2Intervals.set',
        step=1,
        start=500,
        stop=100000,
        quantity=150
    )
