from collections import OrderedDict

# plot climatological means (for selected months) and a time series of area-averages (over land)
from datetime import datetime
from pathlib import Path

# land mask array and basemap objects, can be different
# for different simulations
from matplotlib.gridspec import GridSpec
from mpl_toolkits.basemap import maskoceans
from rpn.domains.rotated_lat_lon import RotatedLatLon
from rpn.rpn import RPN
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


LAND_MASK = None
BASEMAP = None
LONS = None
LATS = None

def get_ym(month_folder: Path=None):
    ym = month_folder.name.split("_")[-1]
    return int(ym[:-2]), int(ym[-2:])


def plot_diags(mean_field, area_avg_series, samples_dir_path: Path, label="", varname=""):

    fig = plt.figure()
    
    gs = GridSpec(1, 2)

    ax = fig.add_subplot(gs[0, 0])
    xx, yy = BASEMAP(LONS, LATS)
    im = BASEMAP.contourf(xx, yy, mean_field, 21, cmap="bwr", ax=ax)
    BASEMAP.colorbar(im)

    ax = fig.add_subplot(gs[0, 1])
    keys = list(area_avg_series.keys())
    data = [area_avg_series[k] for k in keys]
    s = pd.Series(index=keys, data=data)
    s.sort_index(inplace=True)
    s.plot(ax=ax)

    diag_plots = samples_dir_path.parent / "diag_plots"
    diag_plots.mkdir(parents=True, exist_ok=True)
    img_file = diag_plots / f"{varname}_{label}.png"
    fig.savefig(str(img_file), bbox_inches="tight", dpi=300)



def main():
    global BASEMAP, LAND_MASK
    simlabel_to_path = OrderedDict([
        ("NA044_pgi11code_pgicompiled(initial)", "/home/huziy/current_project/Output/test_compilers/NorthAmerica_0.44deg_testPGI_before_gfrefactorings/Samples"),
        ("NA044_pgi11+gfortrancode_pgicompiled", "/home/huziy/current_project/Output/test_compilers/NorthAmerica_0.44deg_testPGI/Samples")
    ])

    varname = "PR"
    filename_prefix = "pm"
    months_of_interest = [1, 2, 12] # only for the 2d map

    for label, path in simlabel_to_path.items():
        path = Path(path)

        # Calculate the required diagnostics
        mean_field, area_avg_series = diagnose_var(varname=varname, fname_prefix=filename_prefix,
                                                   months_list=months_of_interest, samples_folder_path=path)

        # do the plotting
        plot_diags(mean_field, area_avg_series, samples_dir_path=path, label=label, varname=varname)


        # reset global vars to be reused for other simulations
        LAND_MASK = None
        BASEMAP = None


def diagnose_var(varname="PR", fname_prefix="pm", months_list=None, samples_folder_path: Path=None):

    area_avg_series = {}
    current_counter = 0
    current_mean_field = None
    for monthdir in samples_folder_path.iterdir():
        mean_field, counter, area_avg = process_month(varname=varname, fname_prefix=fname_prefix,
                                            months_list=months_list, month_folder_path=monthdir)

        if current_mean_field is None:
            current_mean_field = mean_field
            current_counter = counter
        else:
            w = current_counter / (current_counter + counter)
            current_mean_field = current_mean_field * w + mean_field * (1 - w)

        area_avg_series.update(area_avg)
        
    return current_mean_field, area_avg_series


def process_month(varname="PR", fname_prefix="pm", months_list=None, month_folder_path: Path=None):
    global BASEMAP, LONS, LATS, LAND_MASK
    year, month = get_ym(month_folder_path)

    calculate_mean_map = (month in months_list)

    counter = 0
    fields = []

    for afile in month_folder_path.iterdir():
        # skip other files
        if not afile.name.startswith(fname_prefix):
            continue

        with RPN(str(afile)) as r:
            field = r.variables[varname][:].squeeze()
            fields.append(field)

            if BASEMAP is None:
                LONS, LATS = r.get_longitudes_and_latitudes_for_the_last_read_rec()
                rll = RotatedLatLon(**r.get_proj_parameters_for_the_last_read_rec())
                BASEMAP = rll.get_basemap_object_for_lons_lats(lons2d=LONS, lats2d=LATS)
                LAND_MASK = ~maskoceans(np.where(LONS > 180, LONS - 360, LONS), LATS, LONS, inlands=False).mask

    if calculate_mean_map:
        counter = len(fields)
        mean_field = np.mean(fields, axis=0)
    else:
        mean_field = fields[0] * 0

    return mean_field, counter, {datetime(year, month, 15): np.asarray([field[LAND_MASK].mean() for field in fields]).mean()}


if __name__ == '__main__':
    main()