

import matplotlib
matplotlib.use("Agg")
# plot the timeseries for complete simulation
from pathlib import Path

import pandas as pd
from rpn.rpn import RPN
import matplotlib.pyplot as plt
from rpn.variable import RPNVariable
import argparse


def process_month(mdir:Path, prefix="pm", indices=None, vname="DN") -> list:
    """

    :param mdir:
    :param prefix:
    :param indices: (ix, iy, iz), if iz is omitted, consider 0
    :param vname:
    """

    print("Working on {}".format(mdir))
    if len(indices) == 2:
        indices = indices + (0, )

    result = []
    for afile in mdir.iterdir():

        if not afile.name.startswith(prefix):
            continue

        print("\t ----> {}".format(afile))

        try:
            with RPN(str(afile)) as r:
                i1, i2, i3 = indices
                var = r.variables[vname]
                vals = var[:, i3, i1, i2].squeeze()


                assert isinstance(var, RPNVariable)

                result.append(pd.Series(data=vals, index=var.sorted_dates))

        except KeyError as kerr:
            print("Could not find {} in {}.".format(vname, afile))
            print(kerr)



    print("processed {}".format(mdir))
    return result



def main():

    # defaults
    prefix = "pm"
    vname = "I5"
    indices = (137, 85)

    # parse command line arguments if present
    argparser = argparse.ArgumentParser(description="Plot timeseries from raw model output")
    argparser.add_argument("--varname", nargs="?", default=vname)
    argparser.add_argument("--level_index", nargs="?", default=0, type=int, help="level index in the sorted list")
    args = argparser.parse_args()

    if len(indices) == 2:
        indices = indices + (args.level_index, )
    elif len(indices) == 3:
        indices = list(indices)
        indices[-1] = args.level_index

    print("indices={}; varname={}".format(indices, args.varname))


    samples_path = "/sf1/escer/sushama/huziy/Output/NEI/NEI_WC0.11deg_Crr1/Samples"

    p = Path(samples_path)

    img_dir = Path(p.parent.name)
    if not img_dir.exists():
        img_dir.mkdir()

    selected_data = img_dir / "selected_data"

    if not selected_data.exists():
        selected_data.mkdir()


    all_parts = []
    for mdir in p.iterdir():
        if mdir.is_dir():
            parts = process_month(mdir, prefix=prefix, indices=indices, vname=args.varname)
            all_parts.extend(parts)

    ts = pd.concat(all_parts)
    assert isinstance(ts, pd.Series)


    # save the values for possible further analysis
    selected_data = selected_data / "{}_{}.nc".format(args.varname, "_".join([str(i) for i in indices]))
    ts.to_xarray().to_netcdf(str(selected_data))


    # save the figure
    fig = plt.figure()

    ax = ts.plot()

    ax.set_title(args.varname)

    img_file = img_dir / "{}_{}.png".format(args.varname, "_".join([str(i) for i in indices]))
    fig.savefig(str(img_file), bbox_inches="tight", dpi=400)





if __name__ == '__main__':
    main()