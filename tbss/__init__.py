import os
import os.path as op
is_running_ci_tests = os.environ.get('CI_TEST', 0) == 1
if is_running_ci_tests:
    print('CI_TEST')


def atlasquery(fp, atlas):
    """Run atlasquery and returns the result in a DataFrame. The image is
    assumed to be binary. The atlas should be one of the list given by
    `atlasquery --dumpatlases`.

    Example:
    atlasquery('/tmp/wm_tfce_corr_tstat1.nii.gz',
               'JHU ICBM-DTI-81 White-Matter Labels')
    """
    import subprocess
    import pandas as pd
    from subprocess import PIPE
    cmd = ['atlasquery', '-a', atlas, '-m', fp]

    if not is_running_ci_tests:
        ans = subprocess.run(cmd, stdout=PIPE, stderr=PIPE)
        ans = ans.stdout.decode('utf-8')
    else:
        fp1 = op.join(op.dirname(__file__), 'tests', 'output2.txt')
        ans = open(fp1).read()
    x = {}
    for line in ans.split('\n'):
        if ':' not in line:
            continue
        k, v = line.split(':')
        x[k] = float(v)
    d = {k: v for k, v in sorted(x.items(), key=lambda item: item[1])}

    return pd.DataFrame(list(d.items()), columns=('tract', 'pc'))


def autoaq(fp, atlas, thr=0.95):
    """Run atlasquery (autoaq) and parses the result into two DataFrames. The
    atlas should be one of the list given by `atlasquery --dumpatlases`.

    Example:
    autoaq('/tmp/wm_tfce_corr_tstat1.nii.gz',
            'JHU White-Matter Tractography Atlas',
            thr=0.95)
    """
    def find_del(lines):
        for i, each in enumerate(lines):
            if set(each) == {'-'}:
                return i
        return None

    import tempfile
    import pandas as pd
    import os
    import os.path as op

    f1, fp1 = tempfile.mkstemp(suffix='.txt')
    os.close(f1)

    cmd = ['autoaq', '-i', fp, '-a', '"%s"' % atlas, '-t', str(thr), '-o', fp1]
    if not is_running_ci_tests:
        os.system(' '.join(cmd))
    else:
        fp2 = op.join(op.dirname(__file__), 'tests', 'output1.txt')
        os.system('cp %s %s' % (fp2, fp1))

    if not op.exists(op.abspath(fp)):
        raise FileNotFoundError('File not found %s' % fp)

    if not op.exists(op.abspath(fp1)):
        raise FileNotFoundError('File not found %s. Check command %s'
                                % (fp1, ' '.join(cmd)))

    lines = open(fp1).read().split('\n')
    os.unlink(fp1)

    i1 = find_del(lines)
    if i1 is None:
        return None  # No clusters found
    first_block = lines[1: i1]  # remove first line (filename + atlas name)
    i2 = i1 + find_del(lines[i1+1:]) + 1
    second_block = lines[i1+1:i2]
    third_block = lines[i2+1:]

    # first block
    col = [x for x in first_block[0].split('\t')]
    df1 = pd.DataFrame([x.split('\t') for x in first_block[1:]],
                       columns=col).set_index('ClusterIndex')

    # second block
    col = ['ClusterIndex', 'COG X (mm)', 'COG Y (mm)', 'COG Z (mm)', 'atlas',
           'pc_tract']
    d = [x.split(',') for x in second_block[1:]]
    md = max([len(each) for each in d])
    for i in range(0, md - len(col)):
        col.append('pc_tract%s' % i)

    df2 = pd.DataFrame(d, columns=col)
    df2 = df2[['ClusterIndex', 'pc_tract']].set_index('ClusterIndex')
    df1 = df1.join(df2).reset_index()

    # third block
    ci = None
    d = []
    for line in third_block[2:]:
        if 'Cluster #' in line:
            ci = int(line.split('Cluster #')[1])
        if ci is None:
            continue
        if ':' in line:
            tract, pc = line.split(':')
            d.append([ci, tract, pc])
    col = ['ClusterIndex', 'tract', 'pc']
    df2 = pd.DataFrame(d, columns=col)
    return (df1, df2)
