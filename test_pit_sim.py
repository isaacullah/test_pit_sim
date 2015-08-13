#!/usr/bin/python
import random, sys, os, argparse
try:
    import grass.script as grass
except:
    sys.exit("You must install GRASS GIS in order to run this script.")

#Set up sparse CLI, and make sure there are default values for any parameters not entered
#usage: test_pit_sim.py [-h] [--iters [integer]] [--bounds [integer]] [--padding [integer]] [--sampres [integer]] [--sampint [integer]] [--repeats [integer]] [--sampdist [map name]]
parser = argparse.ArgumentParser(description='This model simulates additive sampling strategies on a known distribution of artifacts.')
parser.add_argument('--iters', metavar='integer', type=int, nargs='?', const=20, default=20, help='The number of steps in the additive sampling routine (per iteration)')
parser.add_argument('--bounds', metavar='integer', type=int, nargs='?', const=1000, default=1000, help='The size of the sampling universe (a square)')
parser.add_argument('--padding', metavar='integer', type=int, nargs='?', const=500, default=500, help='The number of additional units to pad the edges of the sampling universe (to allow for grid rotation, etc)')
parser.add_argument('--sampres', metavar='integer', type=int, nargs='?', const=10, default=10, help='The size of each sampling point (also a square)')
parser.add_argument('--sampint', metavar='integer', type=int, nargs='?', const=100, default=100, help='The interval of the initial sampling points')
parser.add_argument('--repeats', metavar='integer', type=int, nargs='?', const=100, default=100, help='The number of times to shuffle the grid and resample the distribution (number of iterations for the simulation)')
parser.add_argument('--sampdist', metavar='map name', type=str, nargs='?', const="D1_5K", default="D1_5K", help='The artifact distribution to be sampled (a kernel density map)')
# Read in the entered values to internal variables
args = vars(parser.parse_args())
iters = args['iters']
bounds = args['bounds']
padding = args['padding']
sampres = args['sampres']
sampint = args['sampint']
repeats = args['repeats']
sampdist = args['sampdist']
prefix = '%s_%s' % (sampdist,sampint)
# Old non-CLI interface, commented out #
#iters = 20     # number of steps in the additive sampling routine (per iteration)
#bounds = 1250 # size of the sampling universe (a square)
#padding = 500 # number of additional units to pad the edges of the sampling universe (to allow for grid rotation, etc)
#sampres = 10 # size of each sampling point (also a square)
#sampint = 150 # interval of the initial sampling points
#repeats = 500 # the number of times to shuffle the grid and resample the distribution (number of iterations for the simulation)
#sampdist = "D1_5K" # The artifact distribution to be sampled (a kernel density map)
#prefix = "d1_5k_%s" % sampint # The prefix for output maps and stats files

def main(iters,bounds,padding,sampres,sampint,repeats,sampdist,prefix):
    '''Main set of code for the sampling simulation'''
    #set the sample universe size to the maximum boundaries, and  set the resolution to match the sample size
    grass.run_command("g.region", quiet = True, n=(bounds + padding + padding), s=0, e=(bounds + padding + padding), w=0, res=sampres)
    # calculate the real binary presence/absence map for the input distribution (to compare with the sampled presabs)
    realpresab = "%s_real_presab" % prefix
    grass.mapcalc("${realpresab}=if(${sampdist} > 0, 1, 0)", overwrite = True, quiet = True, sampdist = sampdist, realpresab = realpresab)
    #extract the number of squares that have at least one artifact
    truepres = int(grass.parse_command("r.stats", quiet = True, flags="cn", input=realpresab, separator="=")["1"])
    #set up statsfile
    f = open('%s%s%s_stats.csv' % (os.getcwd(), os.sep, prefix), 'w+')
    f.write("Iteration,Positives,True Positives,Difference,Pcnt Difference,R,R2\n")
    f.flush()
    #initiate the outer loop, which will randomly rotate/move the sampling grid within the sampling universe
    pad = len(str(repeats)) # set the zfill pad to match the number of repeats
    for x in range(repeats):
        grass.message("Iteration: %s" % (x + 1))
        jitt1 = random.randint(0,sampint) # get a random seed for the Y offset
        jitt2 = random.randint(0,sampint) # get a random seed for the X offset
        rot = random.randint(0,360) # get a random seed for the grid rotation
        #reset the sample universe size and resolution
        grass.run_command("g.region", quiet = True, n=(bounds + padding - jitt1), s=padding - jitt1, e=(bounds + padding - jitt2), w=padding - jitt2, res=sampres)
        #make the sampling frame from the sampling interval, the current jitter, and the current rotation
        init_grid = "%s_%s_vgridpts" % (prefix,str(x + 1).zfill(pad))
        init_sqrs = "%s_%s_gridpts" % (prefix,str(x + 1).zfill(pad))
        grass.run_command("v.mkgrid", quiet = True, overwrite = True, map=init_grid, box="%s,%s" % (sampint,sampint), angle=rot, type="point")
        grass.run_command("v.to.rast", quiet = True, overwrite = True, input=init_grid, type="point", output=init_sqrs, use="val")
        # zoom out to the padding distance
        grass.run_command("g.region", quiet = True, n=(bounds + padding + padding), s=0, e=(bounds + padding + padding), w=0, res=sampres)
        grass.run_command("r.null", quiet = True, map=init_sqrs, null=0)
        #initiate and start inner loop for the additive sammpling regime
        for i in range(iters):
            if i + 1 == 1:
                old_sqrs = init_sqrs
            else:
                old_sqrs = new_sqrs
            new_sqrs = "%s_itr%s" % (prefix, str(i + 1).zfill(2))
            grass.mapcalc("${new_sqrs}=eval(a=if(${old_sqrs} > 0 && ${sampdist} > 0, 1, 0), b=if(${old_sqrs}[1,0] == 1 || ${old_sqrs}[0,1] == 1 || ${old_sqrs}[-1,0] == 1 || ${old_sqrs}[0,-1] == 1, 1, 0), c=if(b > 0 && ${sampdist} > 0, 1, a), if(isnull(c),0,c))", quiet = True, overwrite = True, old_sqrs = old_sqrs, new_sqrs = new_sqrs, sampdist = sampdist)
        # rename last map to save it
        outmap = "%s_%s" % (prefix,str(x + 1).zfill(pad))
        grass.run_command("g.rename", quiet = True, raster="%s,%s" % (new_sqrs,outmap))
        # pull some stats
        presab = grass.parse_command("r.stats", quiet = True,flags="cn", input=outmap, separator="=")
        try:
            pres = int(presab['1'])
        except:
            pres = 0
        R = grass.parse_command('r.regression.line', flags='g', mapx=realpresab, mapy=outmap)["R"]
        f.write("%s,%s,%s,%s,%s,%s,%s\n" % (x + 1,pres,truepres,truepres - pres,(truepres - pres)/float(truepres),R, float(R) * float(R)))
        f.flush()
    #clean up
    f.close()
    grass.run_command("g.remove", quiet = True, flags = 'f', type = 'raster', pattern = "*_itr*")

if __name__ == "__main__":
    if "GISBASE" not in os.environ:
        sys.exit("You must be in a GRASS GIS session to run this program.")
    main(iters,bounds,padding,sampres,sampint,repeats,sampdist,prefix)
    sys.exit(0)