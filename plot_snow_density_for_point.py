

import matplotlib
matplotlib.use("Agg")
# plot the timeseries for complete simulation
from pathlib import Path

import pandas as pd
from rpn.rpn import RPN
import matplotlib.pyplot as plt
from rpn.variable import RPNVariable


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

    samples_path = "/sf1/escer/sushama/huziy/Output/NEI/NEI_WC0.11deg_Crr1/Samples"


    p = Path(samples_path)

    prefix = "pm"
    vname = "DN"
    indices = (137, 85)

    all_parts = []
    for mdir in p.iterdir():
        if mdir.is_dir():
            parts = process_month(mdir, prefix=prefix, indices=indices, vname=vname)
            all_parts.extend(parts)

    ts = pd.concat(all_parts)
    assert isinstance(ts, pd.Series)

    # save the figure
    fig = plt.figure()

    ax = ts.plot()

    fig.savefig("{}_{}.png".format(vname, "_".join([str(i) for i in indices])))


    pass




if __name__ == '__main__':
    main()