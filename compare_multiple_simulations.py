import calendar

import matplotlib

from util import plot_utils

matplotlib.use("agg")
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
from matplotlib.colors import BoundaryNorm
from matplotlib import cm


LAND_MASK = None
BASEMAP = None
LONS = None
LATS = None

# color levels
vname_to_clevels = {
    "PR": [0, 0.5, 1, 2, 3, 5, 10], 
    "TT": [-20, -15, -10, -5, -2, 0, 2, 5, 10, 15, 20]
}

def get_ym(month_folder: Path = None):
    ym = month_folder.name.split("_")[-1]
    print(f"ym={ym}; mf={month_folder}")
    return int(ym[:-2]), int(ym[-2:])


def plot_diags(mean_field, area_avg_series, samples_dir_path: Path, label="", varname=""):
    global BASEMAP
    fig = plt.figure()

    gs = GridSpec(1, 2)

    ax = fig.add_subplot(gs[0, 1])
    xx, yy = BASEMAP(LONS, LATS)
    
    clevs = vname_to_clevels[varname]
    norm = BoundaryNorm(clevs, len(clevs) - 1) 
    cmap = cm.get_cmap("bwr", len(clevs) - 1)
    im = BASEMAP.contourf(xx, yy, mean_field, levels=clevs, norm=norm, cmap=cmap, ax=ax, extend="both")
    BASEMAP.colorbar(im)
    BASEMAP.drawcoastlines(ax=ax)
    ax.set_xlabel(label)

    ax = fig.add_subplot(gs[0, 0])
    keys = list(area_avg_series.keys())
    data = [area_avg_series[k] for k in keys]
    s = pd.Series(index=keys, data=data)
    s.sort_index(inplace=True)
    s.plot(ax=ax)
    ax.set_title("area average over land")


    diag_plots = samples_dir_path.parent / "diag_plots"
    diag_plots.mkdir(parents=True, exist_ok=True)
    label_fname_part = label.split(",")[0].replace("/", "_")
    img_file = diag_plots / f"{varname}_{label_fname_part}.png"
    fig.savefig(str(img_file), bbox_inches="tight", dpi=150)


def main(simlabel_to_path=None, varname="TT"):
    global BASEMAP, LAND_MASK

    if simlabel_to_path is None:
        simlabel_to_path = OrderedDict([
            ("NA044_pgi11code_pgicompiled(initial)",
             "/home/huziy/current_project/Output/test_compilers/NorthAmerica_0.44deg_testPGI_before_gfrefactorings/Samples"),
            ("NA044_pgi11+gfortrancode_pgicompiled",
             "/home/huziy/current_project/Output/test_compilers/NorthAmerica_0.44deg_testPGI/Samples"),
            ("NorthAmerica_0.44deg_testgfortran_cedar",
             "/home/huziy/current_project/Output/test_compilers/NorthAmerica_0.44deg_testgfortran_cedar/Samples")
        ])


    units_db = {
        "PR": ["mm/day", 1000 * 24 * 3600],
        "TT": ["C", 1],
    }

    fname_prefix_db = {
        "PR": "pm", "TT": "dm"
    }


    filename_prefix = fname_prefix_db[varname]
    months_of_interest = [1, 2, ]  # only for the 2d map
    units, multiplier = units_db[varname]
    

    plot_utils.apply_plot_params(font_size=10)

    for label, path in simlabel_to_path.items():
        path = Path(path)

        # Calculate the required diagnostics
        mean_field, area_avg_series = diagnose_var(varname=varname, fname_prefix=filename_prefix,
                                                   months_list=months_of_interest, samples_folder_path=path)

        # do the plotting
        months_labels = ",".join([calendar.month_name[i][:2] for i in months_of_interest])
        panel_label = f"{label}, {varname} ({units}), \n [months={months_labels}]"
        mean_field *= multiplier
        area_avg_series = {k: v * multiplier for k, v in area_avg_series.items()}
        plot_diags(mean_field, area_avg_series, samples_dir_path=path, label=panel_label, varname=varname)

        # reset global vars to be reused for other simulations
        LAND_MASK = None
        BASEMAP = None


def diagnose_var(varname="PR", fname_prefix="pm", months_list=None, samples_folder_path: Path = None):
    area_avg_series = {}
    current_counter = 0
    current_mean_field = None
    for monthdir in samples_folder_path.iterdir():

        # ignore .DS_Store
        if monthdir.name.startswith("."):
            continue

        print(f" processing {monthdir}")
        mean_field, counter, area_avg = process_month(varname=varname, fname_prefix=fname_prefix,
                                                      months_list=months_list, month_folder_path=monthdir)

        print(f"counter={counter}")

        if counter > 0:
            if current_mean_field is None:
                current_mean_field = mean_field
                current_counter = counter
            else:
                print(current_counter, counter)
                w = current_counter / (current_counter + counter)
                current_mean_field = current_mean_field * w + mean_field * (1 - w)
                current_counter += counter

        area_avg_series.update(area_avg)

    return current_mean_field, area_avg_series


def process_month(varname="PR", fname_prefix="pm", months_list=None, month_folder_path: Path = None):
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

            if varname not in r.variables:
                print(f"{afile} does not contain {varname}, skipping ...")
                continue

            print(f"Processing {afile}")

            field = r.variables[varname][:].squeeze()

            print(field.shape)

            if field.ndim == 2:
                fields.append(field)
            elif field.ndim == 3:
                fields.extend([f for f in field])
            else:
                raise ValueError(
                    f"Can only handle 2d (x, y) and 3d (t, x, y) fields, but got field.shape={field.shape}")

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

    print(f"mean_field.shape={mean_field.shape} ")

    return mean_field, counter, {
        datetime(year, month, 15): np.asarray([field[LAND_MASK].mean() for field in fields]).mean()}



# for science migration
def science_migration_entry():
    simlabel_to_path = OrderedDict([
        ("Guillimin",
         "/gs/project/ugh-612-aa/huziy/Output/v_4.8.12/Output/EUSA/EUSA_0.22_ERA_CLASS26LwithTEB_MODIFIED_GEOPHYS_updated_by_Luis_subset/Samples"),
        ("Science",
         "/gs/project/ugh-612-aa/huziy/Output/v_4.8.12/Output/EUSA/EUSA_0.22_ERA_CLASS26LwithTEB_MODIFIED_GEOPHYS_updated_by_Luis_ECCC_subset/Samples"),
    ])

    var_list = ["TT", "PR"]
    for v in var_list:
        main(simlabel_to_path=simlabel_to_path, varname=v)



if __name__ == '__main__':
    # main()
    science_migration_entry()
