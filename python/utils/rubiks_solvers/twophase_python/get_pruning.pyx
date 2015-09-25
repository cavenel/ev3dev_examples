
def getPruning(table, index):
    """
    Extract pruning value

    Profiling showed this as the #1 hot spot so using cython to speed things up
    """

    if ((index & 1) == 0):
        res = table[index / 2] & 0x0f
    else:
        res = (table[index / 2] & 0xf0) >> 4
    return res
    # return table[index] & 0xf
