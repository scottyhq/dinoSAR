#!/usr/bin/env python3
"""Prepare directory for running topsApp.py on local machine.

Generate interferogram folder containing:
topsApp.xml
SLCs
Orbit files
Aux file


Example
-------

$ prep_topsApp_aws.py -i query.geojson -m 20141130 -s 20141106 -n 1 -r 46.45 46.55 -120.53 -120.43

$ prep_topsApp_aws.py -i query.geojson -t topsApp-template.yml -m 20141130 -s 20141106

Author: Scott Henderson (scottyh@uw.edu)
Updated: 08/2018
"""
import argparse
import os
from dinosar.archive import asf
import dinosar.isce as dice


def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description="prepare ISCE 2.2 topsApp.py")
    parser.add_argument(
        "-i",
        type=str,
        dest="inventory",
        required=True,
        help="Inventory vector file (query.geojson)",
    )
    parser.add_argument(
        "-r", type=str, dest="reference", required=True, help="reference date"
    )
    parser.add_argument(
        "-s", type=str, dest="secondary", required=True, help="secondary date"
    )
    parser.add_argument(
        "-p",
        type=str,
        dest="path",
        required=True,
        help="Path/Track/RelativeOrbit Number",
    )
    parser.add_argument(
        "-n",
        type=int,
        nargs="+",
        dest="swaths",
        required=False,
        choices=(1, 2, 3),
        help="Subswath numbers to process",
    )
    parser.add_argument(
        "-o",
        dest="poeorb",
        action="store_true",
        required=False,
        default=True,
        help="Use precise orbits (True/False)",
    )
    parser.add_argument(
        "-t",
        type=str,
        dest="template",
        required=False,
        help="Path to YAML input template file",
    )
    parser.add_argument(
        "-d", type=str, dest="dem", required=False, help="Path to DEM file"
    )
    parser.add_argument(
        "-b",
        type=float,
        nargs=4,
        dest="roi",
        required=False,
        metavar=("S", "N", "W", "E"),
        help="Region of interest bbox [S,N,W,E]",
    )
    parser.add_argument(
        "-g",
        type=float,
        nargs=4,
        dest="gbox",
        required=False,
        metavar=("S", "N", "W", "E"),
        help="Geocode bbox [S,N,W,E]",
    )
    parser.add_argument(
        "-al", type=int, dest="alooks", required=False, help="Azimuthlooks"
    )
    parser.add_argument(
        "-rl", type=int, dest="rlooks", required=False, help="Rangelooks"
    )
    parser.add_argument(
        "-f", type=float, dest="filtstrength", required=False, help="Filter strength"
    )

    return parser


def main():
    """Run as a script with args coming from argparse."""
    parser = cmdLineParse()
    inps = parser.parse_args()
    gf = asf.load_inventory(inps.inventory)

    if inps.template:
        print(f"Reading from template file: {inps.template}...")
        inputDict = dice.read_yaml_template(inps.template)
    else:
        inputDict = {
            "topsinsar": {
                "sensorname": "SENTINEL1",
                "reference": {"safe": ""},
                "secondary": {"safe": ""},
            }
        }

    intdir = "int-{0}-{1}".format(inps.reference, inps.secondary)
    if not os.path.isdir(intdir):
        os.mkdir(intdir)
    os.chdir(intdir)

    reference_urls = asf.get_slc_urls(gf, inps.reference, inps.path)
    secondary_urls = asf.get_slc_urls(gf, inps.secondary, inps.path)
    downloadList = reference_urls + secondary_urls
    inps.reference_scenes = [os.path.basename(x) for x in reference_urls]
    inps.secondary_scenes = [os.path.basename(x) for x in secondary_urls]

    if inps.poeorb:
        try:
            frame = os.path.basename(inps.reference_scenes[0])
            downloadList.append(asf.get_orbit_url(frame))
            frame = os.path.basename(inps.secondary_scenes[0])
            downloadList.append(asf.get_orbit_url(frame))
        except Exception as e:
            print("Trouble downloading POEORB... maybe scene is too recent?")
            print("Falling back to using header orbits")
            print(e)
            inps.poeorb = False
            pass

    # Update input dictionary with argparse inputs
    inputDict["topsinsar"]["reference"]["safe"] = inps.reference_scenes
    inputDict["topsinsar"]["reference"]["output directory"] = "referencedir"
    inputDict["topsinsar"]["secondary"]["safe"] = inps.secondary_scenes
    inputDict["topsinsar"]["secondary"]["output directory"] = "secondarydir"
    # Optional inputs
    # swaths, poeorb, dem, roi, gbox, alooks, rlooks, filtstrength
    if inps.swaths:
        inputDict["topsinsar"]["swaths"] = inps.swaths
    if inps.dem:
        inputDict["topsinsar"]["demfilename"] = inps.dem
    if inps.roi:
        inputDict["topsinsar"]["regionofinterest"] = inps.roi
    if inps.gbox:
        inputDict["topsinsar"]["geocodeboundingbox"] = inps.gbox
    if inps.filtstrength:
        inputDict["topsinsar"]["filterstrength"] = inps.filtstrength
    if inps.alooks:
        inputDict["topsinsar"]["azimuthlooks"] = inps.alooks
    if inps.rlooks:
        inputDict["topsinsar"]["rangelooks"] = inps.rlooks
    print(inputDict)
    xml = dice.dict2xml(inputDict)
    dice.write_xml(xml)
    # Create a download file
    asf.write_download_urls(downloadList)
    print(f"Generated download-links.txt and topsApp.xml in {intdir}")


if __name__ == "__main__":
    main()
