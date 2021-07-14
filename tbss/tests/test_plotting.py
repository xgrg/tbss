def test_plotting():
    import pyxnat
    import tempfile
    import os
    x = pyxnat.Interface(server='https://central.xnat.org',
                         user='nosetests',
                         password='nose')
    p = x.select.project('nosetests5')
    s = p.subject('rs')
    e = s.experiments().first()
    r = e.resource('BAMOS')
    f = list(r.files('Correct*'))[0]
    fh, fp = tempfile.mkstemp(suffix='.nii.gz')
    os.close(fh)
    f.get(fp)

    from tbss import plotting
    plotting.plot_map(fp, start=0, end=36, step=2)
