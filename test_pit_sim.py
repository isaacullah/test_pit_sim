#!/usr/bin/python
import random, sys, os, argparse
try:
    import grass.script as grass
except:
    sys.exit("You must run this script from within a GRASS GIS session.")

#Set up sparse CLI, and make sure there are default values for any parameters not entered
#usage: test_pit_sim.py [-h] [--iters [integer]] [--bounds [integer]] [--padding [integer]] [--sampres [integer]] [--sampint [integer]] [--repeats [integer]] [--sampdist [map name]]
parser = argparse.ArgumentParser(description='This model simulates additive sampling strategies on a known distribution of artifacts.')
parser.add_argument('--iters', metavar='integer', type=int, nargs='?', const=3, default=3, help='The number of steps in the additive sampling routine (per iteration)')
parser.add_argument('--bounds', metavar='integer', type=int, nargs='?', const=450, default=450, help='The size of the sampling universe (a square)')
parser.add_argument('--padding', metavar='integer', type=int, nargs='?', const=50, default=50, help='The number of additional units to pad the edges of the sampling universe (to allow for grid rotation, etc)')
parser.add_argument('--sampres', metavar='integer', type=int, nargs='?', const=3, default=3, help='The size of each sampling units (also a square)')
parser.add_argument('--sampint', metavar='integer', type=int, nargs='?', const=50, default=50, help='The interval of the initial sampling units')
parser.add_argument('--repeats', metavar='integer', type=int, nargs='?', const=100, default=100, help='The number of times to shuffle the grid and resample the distribution (number of iterations for the simulation)')
parser.add_argument('--sampdist', metavar='map name', type=str, nargs='?', const="", default="", help='The artifact distribution to be sampled (a binary presence/absence map or a density map)')
parser.add_argument('--sites', metavar='map name', type=str, nargs='?', const="Site_areas@gridsim", default="Site_areas@gridsim", help='A binary raster map where areas within sites are coded 1, and areas without are coded 0)')
# Read in the entered values to internal variables
args = vars(parser.parse_args())
iters = args['iters']
bounds = args['bounds']
padding = args['padding']
sampres = args['sampres']
sampint = args['sampint']
resamp = int(round((sampint/sampres)/2,0)) # the interval by which to space new sampling units during the iterative discovery process
grass.message("Resampling distance is %s squares" % resamp)
repeats = args['repeats']
sampdist = args['sampdist']
sites = args['sites']
prefix = '%s_%s' % (sampdist,sampint)

def main(iters,bounds,padding,sampres,sampint,repeats,sampdist,prefix):
    '''Main set of code for the sampling simulation'''
    handle=os.getpid() # grab the pid as a convenient handle for temporary maps
    #set the sample universe size to the maximum boundaries, and  set the resolution to match the sample size
    grass.run_command("g.region", quiet = True, n=(bounds + padding + padding), s=0, e=(bounds + padding + padding), w=0, res=sampres)
    # calculate the real binary presence/absence map for the input distribution (to compare with the sampled presabs)
    realpresab = "%s_real_presab" % prefix
    grass.mapcalc("${realpresab}=if(${sampdist} > 0, 1, 0)", overwrite = True, quiet = True, sampdist = sampdist, realpresab = realpresab)
    #extract the number of squares that have at least one artifact
    truepres = int(grass.parse_command("r.stats", quiet = True, flags="cn", input=realpresab, separator="=")["1"])
    #set up statsfiles
    f = open('%s%s%s_stats.csv' % (os.getcwd(), os.sep, prefix), 'w+')
    f.write("Iteration,Positive Squares,Interpolated Positives,True Positives,Numeric Difference,Percent Difference,R,R2\n")
    f.flush()
    f2 = open('%s%s%s_sites_stats.csv' % (os.getcwd(), os.sep, prefix), 'w+')
    f2.write("Iteration,Inside Positives,Inside Negatives,Outside Positives,Outside Negatives\n")
    f2.flush()
    #initiate the outer loop, which will randomly rotate/move the sampling grid within the sampling universe
    pad = len(str(repeats)) # set the zfill pad to match the number of repeats
    for x in range(repeats):
        grass.message("Iteration: %s" % (x + 1))
        jitt1 = random.randint(0,sampint) # get a random seed for the Y offset
        jitt2 = random.randint(0,sampint) # get a random seed for the X offset
        # rot = random.randint(0,360) # get a random seed for the grid rotation
        #temporarily set the sample universe size and resolution to match the placing of the grid
        grass.run_command("g.region", quiet = True, n=(bounds + padding - jitt1), s=padding - jitt1, e=(bounds + padding - jitt2), w=padding - jitt2, res=sampres)
        #make the sampling frame from the sampling interval, the current jitter, and the current rotation
        init_grid = "%s_%s_initial_squares" % (prefix,str(x + 1).zfill(pad))
        init_sqrs = "%s_%s_gridpts_%s" % (prefix,str(x + 1).zfill(pad), handle)
        # grass.run_command("v.mkgrid", quiet = True, overwrite = True, map=init_grid, box="%s,%s" % (sampint,sampint), angle=rot, type="point")
        grass.run_command("v.mkgrid", quiet = True, overwrite = True, map=init_grid, box="%s,%s" % (sampint,sampint), type="point")
        # reset the region as it was initially
        grass.run_command("g.region", quiet = True, n=(bounds + padding + padding), s=0, e=(bounds + padding + padding), w=0, res=sampres)
        #set up the first sample units
        grass.run_command("v.to.rast", quiet = True, overwrite = True, input=init_grid, type="point", output=init_sqrs, use="val")
        grass.run_command("r.null", quiet = True, map=init_sqrs, null=0)
        #initiate and start inner loop for the additive sammpling regime
        for i in range(iters):
            if i + 1 == 1:
                old_sqrs = init_sqrs
                new_sqrs = "%s_%s_%s" % (prefix, str(i + 1).zfill(2), handle)
                grass.mapcalc("${new_sqrs}=if(${old_sqrs} > 0 && ${sampdist} > 0, 1, if(${old_sqrs} > 0 && ${sampdist} <=  0, 0, -1))", quiet = True, overwrite = True, new_sqrs = new_sqrs, old_sqrs = old_sqrs, sampdist = sampdist)
            else:
                old_sqrs = new_sqrs
                new_sqrs = "%s_%s_%s" % (prefix, str(i + 1).zfill(2), handle)
                #tempmap =  "%s_checkme_%s_%s" % (prefix, str(x + 1).zfill(pad), str(i + 1).zfill(2)) #"temporary_map%s_itr%s" % (prefix, str(i + 1).zfill(2))
                #grass.mapcalc("${tempmap}=if(${old_sqrs} > 0 && ${sampdist} > 0, 1, if(${old_sqrs} > 0 && ${sampdist} <=  0, -1, null()))", quiet = True, overwrite = True, tempmap = tempmap, old_sqrs = old_sqrs, sampdist = sampdist)
                #grass.mapcalc("${new_sqrs}=eval(a=if(${tempmap}[${resamp},0] == 1 || ${tempmap}[0,${resamp}] == 1 || ${tempmap}[-${resamp},0] == 1 || ${tempmap}[0,-${resamp}] == 1, 1, 0), if(a == 1 && ${sampdist} > 0, 1, if(a == 1 && ${sampdist} <= 0, -1, ${tempmap})))", quiet = True, overwrite = True, tempmap = tempmap, new_sqrs = new_sqrs, sampdist = sampdist, resamp = resamp)
                grass.mapcalc("${new_sqrs}=eval(a=if(${old_sqrs}[${resamp},0] == 1 || ${old_sqrs}[0,${resamp}] == 1 || ${old_sqrs}[-${resamp},0] == 1 || ${old_sqrs}[0,-${resamp}] == 1, 1, 0), if(a == 1 && ${sampdist} > 0, 1, if(a == 1 && ${sampdist} <= 0, 0, ${old_sqrs})))", quiet = True, overwrite = True, old_sqrs = old_sqrs, new_sqrs = new_sqrs, sampdist = sampdist, resamp = resamp)
        # rename last map to save it
        outmap = "%s_%s" % (prefix,str(x + 1).zfill(pad))
        grass.run_command("g.rename", quiet = True, raster="%s,%s" % (new_sqrs,outmap))
        # replace "-1" with NULL
        grass.run_command("r.null", quiet = True, map = outmap, setnull=-1)
        # interpolate a density surface from sample
        dsurf = "%s_%s_dens_surf_%s" % (prefix,str(x + 1).zfill(pad), handle)
        grass.run_command("r.fillnulls", quiet=True, overwrite=True, input=outmap, output=dsurf, method="bicubic")
        # turn density surface into presab to compare to real presab map via regression analysis
        outpres = "%s_%s_interp_pres" % (prefix,str(x + 1).zfill(pad))
        grass.mapcalc("${outpres}=eval(a=round(${dsurf}), if(a >= 1, 1, 0))", quiet=True, overwrite=True, dsurf=dsurf, outpres=outpres)
        # pull some general stats
        presab = grass.parse_command("r.stats", quiet = True,flags="cn", input=outmap, separator="=")
        interp_presab = grass.parse_command("r.stats", quiet = True,flags="cn", input=outpres, separator="=")
        try:
            pres = int(presab['1'])
        except:
            pres = 0
        try:
            intpres = int(interp_presab['1'])
        except:
            intpres = 0
        R = grass.parse_command('r.regression.line', flags='g', mapx=realpresab, mapy=outpres)["R"]
        f.write("%s,%s,%s,%s,%s,%s,%s,%s\n" % (x + 1,pres,intpres,truepres,truepres - intpres,(truepres - intpres)/float(truepres),R, float(R) * float(R)))
        f.flush()
        # pull some site stats
        sites_stats = grass.read_command("r.stats", quiet = True,flags="cn", input="%s,%s" % (sites,outmap), separator=",")
        site_negs = 0
        site_pos = 0
        out_negs = 0
        out_pos = 0
        for lines in sites_stats.split('\n'):
            line=lines.split(',')
            if line[0] is '1' and line[1] is '0':
                site_negs = line[2]
            if line[0] is '1' and line[1] is '1':
                site_pos = line[2]
            if line[0] is '0' and line[1] is '0':
                out_negs = line[2]
            if line[0] is '0' and line[1] is '1':
                out_pos = line[2]
            else:
                pass
        f2.write("%s,%s,%s,%s,%s\n" % (x+1,site_pos,site_negs,out_pos,out_negs))
        f.flush()
    #clean up
    f.close()
    f2.close()
    grass.run_command("g.remove", quiet = True, flags = 'f', type = 'raster', pattern = "*%s" % handle)

if __name__ == "__main__":
    if "GISBASE" not in os.environ:
        sys.exit("You must be in a GRASS GIS session to run this program.")
    main(iters,bounds,padding,sampres,sampint,repeats,sampdist,prefix)
    sys.exit(0)
