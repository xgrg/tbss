def dump(df, fp):
    '''Converts a design matrix from pandas DataFrame to a TBSS-ready .mat
    file.'''

    if 'images' in df.columns:
        del df['images']

    covlist = df.columns
    mat = ['/NumWaves %s'%len(covlist)]
    mat.append('/NumPoints %s'%len(df))
    mat.append('/Matrix')
    for row_index, row in df.iterrows():
        s1 = ' '.join([str(row[e]) for e in covlist])
        mat.append(s1)

    s = '\n'.join(mat)
    with open(fp, 'w') as w:
        w.write(s)

def read(fp):
    ''' Read a matrix from a TBSS .mat file.'''

    import logging as log
    lines = open(fp).read().split('\n')
    lines = [line for line in lines if not line.startswith('/')]
    mat = []
    for line in lines:
        mat.append(line.split(' '))
    return mat
