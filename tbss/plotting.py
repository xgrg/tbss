from matplotlib import pyplot as plt
from matplotlib import cm

plt.rcParams.update({'figure.max_open_warning': 0})


def plot_stat_map(img, mean_FA_skeleton, start, end, row_l=6, step=1, title='',
                  axis='z', pngfile=None, threshold=0.95):
    """ Inspired from plot_two_maps. Plots a TBSS contrast map over the
    skeleton of a mean FA map"""

    from nilearn import plotting
    from PIL import Image
    import io
    import tempfile
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


def plot_atlas(img, mean_FA_skeleton, start, end, row_l=6, step=1, title='',
               axis='z', pngfile=None):
    """ Generates a multiple row plot from a ROI image. """

    from nilearn import plotting
    from PIL import Image
    import tempfile
    import logging as log

    slice_nb = int(abs(((end - start) / float(step))))
    images = []

    for line in range(int(slice_nb/float(row_l) + 1)):
        opt = {'roi_img': img,
               'bg_img': mean_FA_skeleton,
               'title': {True: title,
                         False: None}[line == 0],
               'black_bg': True,
               'display_mode': axis,
               'cut_coords': range(start + line * row_l * step,
                                   start + (line+1) * row_l * step,
                                   step)}
        method = 'plot_roi'

        t = getattr(plotting, method).__call__(**opt)

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


def plot_map(img, start, end, step=1, row_l=6, title='', bg_img=None,
             threshold=None, axis='z', method='plot_stat_map', overlay=None,
             pngfile=None, cmap=None):
    ''' Generates a multiple row plot instead of the very large native plot,
    given the number of slices on each row, the index of the first/last slice
    and the increment.

    Method parameter can be plot_stat_map (default) or plot_prob_atlas.'''

    from nilearn import plotting, image
    import io
    from PIL import Image
    img = image.math_img("np.ma.masked_less(img, 0)", img=img)

    slice_nb = int(abs(((end - start) / float(step))))
    images = []
    for line in range(int(slice_nb/float(row_l) + 1)):
        opt = {'title': {True: title,
                         False: None}[line == 0],
               'colorbar': True,
               'black_bg': True,
               'display_mode': axis,
               'threshold': threshold,
               'cut_coords': range(start + line * row_l * step,
                                   start + (line+1) * row_l * step,
                                   step)}
        if method == 'plot_prob_atlas':
            opt.update({'maps_img': img,
                        'view_type': 'contours'})
        elif method == 'plot_stat_map':
            opt.update({'stat_map_img': img})
        if bg_img is not None:
            opt.update({'bg_img': bg_img})
        if cmap is not None:
            opt.update({'cmap': getattr(cm, cmap)})

        t = getattr(plotting, method).__call__(**opt)

        # Add overlay
        if overlay is not None:
            if isinstance(overlay, list):
                for each in overlay:
                    t.add_overlay(each)
            else:
                t.add_overlay(overlay)

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
        import tempfile
        pngfile = tempfile.mkstemp(suffix='.png')[1]
    print('Saving to... %s' % pngfile)

    out.save(pngfile, dpi=(200, 200))
    return pngfile


def sections_allcontrasts(path, title, contrasts='all', mode='uncorrected',
                          axis='z', row_l=8, start=-32, end=34, step=2):
    ''' For each SPM contrast from a Nipype workflow (`path` points to the base
    directory), generates a figure made of slices from the corresponding
    thresholded map.

    `mode` can be either 'uncorrected' (p<0.001, T>3.1, F>4.69)
                      or 'FWE' (p<0.05, T>4.54, F>8.11).
    `title` is the title displayed on the plot.'''

    import gzip, pickle
    import os.path as op
    from glob import glob

    nodes = [pickle.load(gzip.open(op.join(path, e, '_node.pklz'), 'rb'))
             for e in ['modeldesign', 'estimatemodel', 'estimatecontrasts']]
    _, _, node = nodes

    def _thiscontrast(i, node=node, mode=mode, title=title, axis=axis,
                      row_l=row_l, start=start, end=end, step=step):
        output_dir = op.join(path, node._id)
        img = glob(op.join(output_dir, 'spm*_00%02d.nii'%i))[0]
        contrast_type = op.split(img)[-1][3]
        print([img, contrast_type])
        contrast_name = node.inputs.contrasts[i-1][0]
        # from nilearn.glm import threshold_stats_img
        # thresholded_map1 = threshold_stats_img(img, threshold=0.001,
        #     cluster_threshold=cluster_threshold)
        if mode == 'uncorrected':
            threshold1 = 3.106880 if contrast_type == 'T' else 4.69
            pval_thresh = 0.001
            #threshold1 = 2.59 if contrast_type == 'T' else 4.69
            #pval_thresh = 0.005
        elif mode == 'FWE':
            threshold1 = 4.5429 if contrast_type == 'T' else 8.1101
            pval_thresh = 0.05
        params = (title, contrast_name, contrast_type, threshold1, pval_thresh,
                  mode)
        title = '(%s) %s - %s>%.02f - p<%s (%s)' % params
        p = plot_map(img, threshold=threshold1, row_l=row_l, axis=axis,
                     start=start, end=end, step=step, title=title)
        return p

    sections = []
    for i in range(1, len(node.inputs.contrasts)+1):
        cname = node.inputs.contrasts[i-1][0]
        is_in_contrasts = isinstance(contrasts, list) and i in contrasts
        is_a_contrast = isinstance(contrasts, str) and (contrasts == 'all'
                                                        or contrasts in cname)
        if is_in_contrasts or is_a_contrast:
            pngfile = _thiscontrast(i)
            sections.append((cname, pngfile))
    return sections
