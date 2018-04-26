# test_pit_sim.py

#### This model simulates additive sampling strategies on a known distribution of artifacts. It requires GRASS GIS, and must be invoked from within a GRASS GIS session.


## Usage
For basic usage, copy script to current working directory, and from within a GRASS session, run:       

`test_pit_sim.py -h`

optional arguments:
   
    `-h, --help           Show this help message and exit
    --iters [integer]     The number of steps in the additive sampling routine (per iteration)
    --bounds [integer]    The size of the sampling universe (a square)
    --padding [integer]   The number of additional units to pad the edges of thesampling universe (to allow for grid rotation, etc)
    --sampres [integer]  The size of each sampling unit (also a square)
    --sampint [integer]   The interval of the initial sampling units
    --repeats [integer]   The number of times to shuffle the grid and resample the
 distribution (number of iterations for simulation)
    --sampdist [map name] The artifact distribution to be sampled (a kernel density. map)`

## GRASS Location CRS
For best results, you should run this script in an "unprojected" XY GRASS location. It *should* also work in any projected CRS with linear measurements (e.g., UTM projections). Do not use an angular CRS like LatLong.

## Input artifact density map
The module requires an existing raster map of artifact densities (or presence/absence). This map must be in the GRASS mapset of the current GRASS session. A random artifact scatter can be created with the GRASS module _r.random_. More complex artifact distributions can be created with a combination of *v.random* > *v.buffer* > *v.to.rast* > *r.random* (or *v.random* > *r.kernel.density*). It is important that the final distribution map not contain any nulls (i.e., any areas without artifacts should contain value 0, not NULL). If necessary, replace nulls with zeros using *r.nulls*.

## The additive sampling routine
The module will sample the created distributon with an initial set of sampling locations, laid out at the vertices of a square grid of spacing *--sampint*. The size of the sampling locations is determined by *--sampres*. Sample locations are also square in shape. If any sample returns positive (presence of one or more artifacts), four additional sampling units are created immediately adjacent to the positive sample in the four cardinal directions. This process is repeated *--iters* number of times, each time adding new samples around previous postive returns. The additive sampling routine results in a final presence/absence map where value 1 means that the cumulative additive sampling routine discovered at least one artifact in a sample unit, and value 0 means that either there were no artifacts found in a sampled location or that the location was not sampled. The module will repeat this process for *--repeats* number of sampling grids. Each sampling grid will share the same *--sampint* and *--sampres*, as entered, but will be randomly moved along the x and y axes, as well as randomly rotated around the z axis. Thus, each repetition uses the same initial sampling interval and geometry, but not the same starting locations. In other words, the orientation of the sampling frame to the sampled distribution is changed in each iteration, which allows for a more accurate estimate of the error associated with any particular sampling geometry for any particular sampled distribution of artifacts.


## Statistics
After each iteration, the module will compare the resultant presence/absence map with a presence/absence map created directly from the input artifact distribution. Two basic sets of comparative data are recorded: 1) the number of positive samples in the sampled distribution compared to the actual number of presences in the original distribution, and, 2) the R and R^2 value of a linear regression of the sampled distribution to the original distribution. The statistics are saved to an output text file (see below).


## Outputs
Output will include many GRASS maps of the sampled distribution, and an ASCII text file containing statistics. Output maps will be prefixed by the name of the input distribution map and the sampling interval. The output stats file will use the same prefix, and will be output in the current working directory.
