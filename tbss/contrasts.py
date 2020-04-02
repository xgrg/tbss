def main_effects(covlist):
    '''Return a set of main effect contrasts based on a list of covariates.
    Each item from the list gives two opposite vectors full of zeros with a
    one at the position of the corresponding covariate in the list.'''

    con = []
    for i, each in enumerate(covlist):
        c = [0] * len(covlist)
        c[i] = 1
        con.append(('%s(+)'%each, list(c)))
        c[i] = -1
        con.append(('%s(-)'%each, c))
    return con

def pairwise_contrasts(var, covlist):
    '''Return a set of pairwise contrasts between items in a list
    taken from a whole list of covariates.'''

    import itertools
    con = []
    for i, j in itertools.permutations(var, 2):
        c = [0] * len(covlist)
        c[covlist.index(i)] = 1
        c[covlist.index(j)] = -1
        con.append(('%s>%s'%(i,j), c))
    return con

def dump(contrasts, fp):
    '''Stores a collection of contrasts in one or multiple file(s)
    dispatching them in equally sized chunks.'''

    def __build_file__(contrasts, mock=0):
        con = ['/NumWaves %s'%len(contrasts[0][1])]

        contrasts2 = []
        for i in range(0, mock):
            contrasts2.append(('mock%s'%(i+1), [0]*len(contrasts[0][1])))
        contrasts2.extend(contrasts)

        for i, (name, contrast) in enumerate(contrasts2):
            con.append('/ContrastName%s %s'%(i+1, name))
        nb_contrasts = len(contrasts2)
        con.append('/NumContrasts %s'%str(nb_contrasts))
        con.append('/Matrix')
        for i, (name, c) in enumerate(contrasts2):
            con.append(' '.join([str(each) for each in c]))

        return '\n'.join(con)

    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    import math

    if isinstance(fp, str):
        fp = [fp]
    chunk_size = math.ceil(len(contrasts)/len(fp))
    con_size = len(contrasts[0][1])
    for n,c in contrasts:
        if len(c) != con_size:
            raise Exception('Size mismatch in contrasts')
    for i, (each, f) in enumerate(zip(chunks(contrasts, int(chunk_size)), fp)):
        with open(f, 'w') as w:
            w.write(__build_file__(each, mock=int(i*chunk_size)))

def read(fp):
    ''' Read a list of contrasts from a TBSS .con file.'''

    import logging as log
    lines = open(fp).read().split('\n')
    names_lines = [line for line in lines if line.startswith('/ContrastName')]
    contrasts_lines = [line for line in lines if not line.startswith('/')]
    con = []
    for name, contrast in zip(names_lines, contrasts_lines):
        con.append((' '.join(name.split(' ')[1:]), contrast.split(' ')))
    return con

def to_dataframe(con):
    ''' Turns a set of contrasts in a DataFrame.'''
    names = [e[0] for e in con]
    val = [[float(each) for each in e[1:][0]] for e in con]
    import pandas as pd
    df = pd.DataFrame(val, index=names)
    return df

# Building the `randomise` commands
def randomise_parallel(in_file, out_basename, design_mat, mask, tcon,
        num_perm=1000, demean=False, n_cpus=6, sleep_interval=120,
        email_notify=None):
    ''' Generate `randomise` commands with proper options given a number of
    available cpus. Wait `sleep_interval` seconds before running the next one
    and send email notifications (start/end) to `email_notify` if an email
    address is provided.'''

    import os.path as op
    import nipype.interfaces.fsl as fsl
    from nipype import logging
    import tempfile, os
    log = logging.getLogger('nipype.workflow')

    contrasts = read(tcon)
    fp = [op.join(op.dirname(out_basename), '%s_part%s.con'%(op.basename(out_basename), str(s))) \
            for s in range(0, min(n_cpus, len(contrasts)))]

    log.info('Temporary contrast files: %s'%str(fp))
    dump(contrasts, fp)

    commands = []
    for i in range(0, min(n_cpus, len(contrasts))):
        rand = fsl.Randomise(in_file=in_file, mask=mask, tcon=fp[i],
            design_mat=design_mat, demean=demean, num_perm=num_perm,
            raw_stats_imgs=True, tfce2D=True)

        skipTo = i+1
        tmpfile = tempfile.mkstemp(suffix='.log')
        os.close(tmpfile[0])
        tmpfile = tmpfile[1]

        cmd = rand.cmdline.replace('-o "randomise"',
                '-o %s --skipTo=%s -V'%(out_basename, skipTo))
        cmd = cmd + ' &> %s'%tmpfile
        commands.append(cmd)

    if not email_notify is None:
        notif_commands = []
        for i, e in enumerate(commands):
            prefix = 'mailx -s "%s %s %s %s" < /dev/null "%s"'\
                    %(contrasts[i][0], tcon, e.split('&>')[-1], '%s', email_notify)
            cmd = '%s ; %s ; %s'%(prefix%'started', e, prefix%'ended')
            notif_commands.append(cmd)
        commands = notif_commands

    if not sleep_interval is None and sleep_interval > 0:
        commands = ['sleep %s ; %s'%(str(i*sleep_interval), e) \
                for i, e in enumerate(commands)]


    return commands
