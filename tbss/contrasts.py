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
        for i in xrange(mock):
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
    chunk_size = math.ceil(len(contrasts)/len(fp))
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
    import tempfile
    log = logging.getLogger('workflow')

    contrasts = read(tcon)
    fp = ['/tmp/%s_part%s.con'%(op.basename(out_basename), str(s)) \
            for s in xrange(n_cpus)]

    log.info('Temporary contrast files: %s'%str(fp))
    dump(contrasts, fp)

    commands = []
    for i in xrange(n_cpus):
        rand = fsl.Randomise(in_file=in_file, mask=mask, tcon=fp[i],
            design_mat=design_mat, demean=demean, num_perm=num_perm,
            raw_stats_imgs=True, tfce2D=True)

        skipTo = i+1
        tmpfile = tempfile.mkstemp(suffix='.log')[1]

        cmd = rand.cmdline.replace('-o "tbss_"',
                '-o %s --skipTo=%s -V &> %s'%(out_basename, skipTo, tmpfile))
        commands.append(cmd)

    if not sleep_interval is None and sleep_interval > 0:
        commands = ['sleep %s ; %s'%(str(i*sleep_interval), e) \
                for i, e in enumerate(commands)]

    if not email_notify is None:
        notif_commands = []
        for i, e in enumerate(commands):
            prefix = 'mailx -s "%s %s" < /dev/null "%s"'\
                    %(contrasts[i][0], '%s', email_notify)
            cmd = ['%s ; %s ; %s'%(prefix%'started', e, prefix%'ended') \
                    for e in commands]
            notif_commands.append(cmd)
        commands = notif_commands

    return commands