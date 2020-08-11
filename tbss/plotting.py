from matplotlib import pyplot as plt
plt.rcParams.update({'figure.max_open_warning': 0})


def plot_stat_map(img, mean_FA_skeleton, start, end, row_l=6, step=1, title='',
                  axis='z', pngfile=None, threshold=0.95):
    """ Inspired from plot_two_maps. Plots a TBSS contrast map over the
    skeleton of a mean FA map"""

    from nilearn import plotting
    from PIL import Image
    import io
    import tempfile
    from matplotlib import cm
    import logging as log

    # Dilate tbss map
    import numpy as np
    from skimage.morphology import cube, dilation
    from nilearn import image
    d = np.array(image.load_img(img).dataobj)
    dil_tbss = dilation(d, cube(2))
    dil_tbss_img = image.new_img_like(img, dil_tbss)

    slice_nb = int(abs(((end - start) / float(step))))
    images = []

    for line in range(int(slice_nb/float(row_l) + 1)):
        opt = {'title': {True: title,
                         False: None}[line == 0],
               'colorbar': False,
               'black_bg': True,
               'display_mode': axis,
               'threshold': 0.2,
               'cmap': cm.Greens,
               'cut_coords': range(start + line * row_l * step,
                                   start + (line+1) * row_l * step,
                                   step)}
        method = 'plot_stat_map'
        opt.update({'stat_map_img': mean_FA_skeleton})

        t = getattr(plotting, method).__call__(**opt)

        try:
            # Add overlay
            t.add_overlay(dil_tbss_img, cmap=cm.hot, threshold=threshold,
                          colorbar=True)
        except TypeError:
            log.info('probably empty tbss map')
            pass

        # Converting to PIL and appending it to the list
        buf = io.BytesIO()
        t.savefig(buf)
        buf.seek(0)
        im = Image.open(buf)
        images.append(im)

    # Joining the images
    imsize = images[0].size
    out = Image.new('RGBA', size=(imsize[0], len(images)*imsize[1]))
    for i, im in enumerate(images):
        box = (0, i * imsize[1], imsize[0], (i+1) * imsize[1])
        out.paste(im, box)

    if pngfile is None:
        pngfile = tempfile.mkstemp(suffix='.png')[1]
    log.info('Saving to... %s (%s)' % (pngfile, title))

    out.save(pngfile)
