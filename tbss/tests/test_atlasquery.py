import tbss


def test_autoaq():
    import os.path as op
    fakedata = op.join(op.dirname(__file__), 'output2.txt')
    tbss.autoaq(fakedata, 'fakeatlas')


def test_atlasquery():
    tbss.atlasquery('/tmp/fakedata.nii.gz', 'fakeatlas')
