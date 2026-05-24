from IPython.display import Image
import numpy as np
import os
import subprocess
import sys
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.image import imread
from matplotlib.colors import LogNorm


## Run Command - cd C:\openmc-uni
## Run Command - python OpenMC-Iridium-Shielding.py
Plot_Dimension = 500
SeedLocation_x = 0
SeedLocation_y = 5
SeedLocation_z = 0


## ---------------Gets CMD to open and run from Idle and also run Docker-------------------------------------
def inside_docker() -> bool:
    return os.path.exists("/.dockerenv")

if not inside_docker():
    print(" Launching OpenMC in Docker...")

    current_dir = os.getcwd().replace("\\", "/")
    script_name = os.path.basename(__file__)

    cmd = [
        "docker", "run", "-it", "--rm",
        "-v", f"{current_dir}:/mnt",
        "-w", "/mnt",
        "openmc/openmc",
        "python3", f"/mnt/{script_name}"
    ]

    subprocess.run(cmd, check=True)
    input("\n Docker run finished. Press Enter to close this window...")
    sys.exit(0)


import openmc


## -------------------Add Emissions--------------------------------------------------------------------------------
##Variables for Source
energies = [317000, 468000, 604000]  # eV
intensities = [0.5897, 0.345, 0.058]  #From data sheet divided by Sum
Emissions_per_decay =2.2#https://www.sciencedirect.com/topics/nursing-and-health-professions/iridium-192
Length = 0.34#cm
Activity = 10000 


radius_dist = openmc.stats.Uniform(0.0, 0.0345)      # radius(cm)
phi_dist = openmc.stats.Uniform(0.0, 2* 3.14159)     # Sources all the way round the circle
Length_dist = openmc.stats.Uniform(-Length/2, Length/2)     # length (cm)

cyl_space = openmc.stats.CylindricalIndependent(r=radius_dist, phi=phi_dist, z=Length_dist, origin=(SeedLocation_x ,SeedLocation_y,SeedLocation_z))


source = openmc.IndependentSource(space=cyl_space)
#source.space = cyl_space
#source.angle = openmc.stats.Monodirectional(reference_uvw=(0, 1, 0))  # Along +z
source.angle = openmc.stats.Isotropic() #Emits in all directions
source.energy = openmc.stats.Discrete(energies, intensities)
source.particle = "photon"

print(source)

# ------------------- Materials -------------------
titanium = openmc.Material(name="Titanium Capsule")
titanium.add_element("Ti", 1.0)
titanium.set_density("g/cm3", 4.5)

argon = openmc.Material(name="Argon")
argon.add_element("Ar", 1.0)
argon.set_density("g/cm3", 0.00178)

water = openmc.Material(name="Water")
water.add_nuclide("H1", 2.0)
water.add_nuclide("O16", 1.0)
water.set_density("g/cm3", 1.0)

muscle = openmc.Material(name="Muscle")
muscle.set_density('g/cm3', 1.040)  # density from NIST table

#https://physics.nist.gov/cgi-bin/Star/compos.pl?refer=ap&matno=201
muscle.add_element("H", 0.100637, "wo")
muscle.add_element("C", 0.107830, "wo")
muscle.add_element("N", 0.027680, "wo")
muscle.add_element("O", 0.754773, "wo")
muscle.add_element("N", 0.000750,"wo")
muscle.add_element("Mg", 0.000190, "wo")
muscle.add_element("P", 0.001800, "wo")
muscle.add_element("S", 0.002410, "wo")
muscle.add_element("Cl", 0.000790, "wo")
muscle.add_element("K", 0.003020, "wo")
muscle.add_element("Ca", 0.000030, "wo")
muscle.add_element("Fe", 0.000040, "wo")
muscle.add_element("Zn", 0.000050, "wo") 


shielding = openmc.Material(name="Shielding")
shielding.add_element("W",1.0)# Tungsten 
shielding.set_density("g/cm3", 19.25)# Thungsten's Density

#https://physics.nist.gov/cgi-bin/Star/compos.pl?refer=ap&matno=104
air = openmc.Material(name="air")
air.set_density('g/cm3', 1.20479e-3)
air.add_element("C",0.000124,"wo")
air.add_element("N",0.755267,"wo")
air.add_element("O",0.231781,"wo")
air.add_element("Ar",0.012827,"wo")

robotarm = openmc.Material(name="Robotarm Electronics")
robotarm.add_element("Cu",1.0)
robotarm.set_density("g/cm3", 8.96)

robotarm_electronics = openmc.Material(name="Arm Material")
robotarm_electronics.add_element("Al",1.0)
robotarm_electronics.set_density("g/cm3", 2.7)

materials = openmc.Materials([titanium, argon, water,shielding,muscle,air,robotarm,robotarm_electronics])
materials.cross_sections = "cross_sections/endfb71/endfb-vii.1-hdf5/cross_sections.xml"
materials.export_to_xml()

# ------------------- Geometry -------------------
# Planes for capsule
x_min = openmc.XPlane(x0=(-0.225+SeedLocation_x))
x_max = openmc.XPlane(x0=(0.225+SeedLocation_x))
x_inner_min = openmc.XPlane(x0=(-0.17+SeedLocation_x))
x_inner_max = openmc.XPlane(x0=(0.17+SeedLocation_x))
r_outer = openmc.XCylinder(r=0.04,y0=SeedLocation_y,z0=SeedLocation_z)
r_inner = openmc.XCylinder(r=0.0345,y0=SeedLocation_y,z0=SeedLocation_z)

# Hollow titanium cylinder
outer_tube = +x_min & -x_max & -r_outer
inner_void = +x_inner_min & -x_inner_max & -r_inner
capsule_region = outer_tube & ~inner_void

capsule_cell = openmc.Cell(region=capsule_region)
capsule_cell.fill = titanium

# Argon inside capsule
argon_region = inner_void
argon_cell = openmc.Cell(region=argon_region)
argon_cell.fill = argon
#argon_cell.fill = None # Vacuum

# Body sphere outside
sphere_surface = openmc.Sphere(r=20.0)
body_region = -sphere_surface & ~capsule_region 
body_cell = openmc.Cell(region=body_region)
body_cell.fill = muscle

#-------------------------------------Robot Arm Base-------------------------------------------------

Base_Thickness = 5
Base = openmc.YCylinder(r=14,x0=110,z0=0)
Base_inner = openmc.YCylinder(r=14-Base_Thickness,x0=110,z0=0)
Base_height_max = openmc.YPlane(y0=44) 
Base_height_min = openmc.YPlane(y0=0)
Base_height_max_inner = openmc.YPlane(y0=44-Base_Thickness) 
Base_height_min_inner = openmc.YPlane(y0=0+Base_Thickness)

Inner_void = -Base_height_max_inner & +Base_height_min_inner & -Base_inner
Base_region = -Base_height_max & +Base_height_min & -Base & ~Inner_void
Base_cell = openmc.Cell(region=Base_region)
Base_cell.fill = robotarm
#-------------------------------------Inner Copper Base (ICB)-------------------------------------------------

ICB = openmc.YCylinder(r=2,x0=110,z0=0)
ICB_region = -Base_height_max & +Base_height_min & -ICB
ICB_cell = openmc.Cell(region=ICB_region)
ICB_cell.fill = robotarm_electronics


#-------------------------------------Robot Arm Section 1-------------------------------------------------
a_prime = 1
b_prime = 1
c_prime = 0
Length_Section_1 = 89
Thickness_Section_1 = 15
d1_prime = -120
d2_prime = 40
m = Thickness_Section_1/(np.cos((np.pi/2)-(np.atan(b_prime/a_prime))))
n=Length_Section_1/(np.cos((np.pi/2)-np.atan(b_prime/a_prime)))

Plane_1 = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime)
Plane_2 = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime-m)
Plane_3 = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime)
Plane_4 = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime-n)
Plane_5 = openmc.ZPlane(z0 = 30)#20
Plane_6 = openmc.ZPlane(z0= 14)#-1


Inner_Thickness = 0.5
Length_Section_1_inner = 89-2*Inner_Thickness
Thickness_Section_1_inner = 15-2*Inner_Thickness
d1_prime_inner = -120-Inner_Thickness
d2_prime_inner = 40-Inner_Thickness
m = Thickness_Section_1_inner/(np.cos((np.pi/2)-(np.atan(b_prime/a_prime))))
n=Length_Section_1_inner/(np.cos((np.pi/2)-np.atan(b_prime/a_prime)))

Plane_1_inner = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime_inner)
Plane_2_inner = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime_inner-m)
Plane_3_inner = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime_inner)
Plane_4_inner = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime_inner-n)
Plane_5_inner = openmc.ZPlane(z0 = 30)#20
Plane_6_inner = openmc.ZPlane(z0= 14)#-1
Section_1_region_inner = -Plane_1_inner & +Plane_2_inner &-Plane_3_inner & +Plane_4_inner & -Plane_5_inner & +Plane_6_inner & ~Base_region


Section_1_region = -Plane_1 & +Plane_2 &-Plane_3 & +Plane_4 & -Plane_5 & +Plane_6 & ~Base_region &~Section_1_region_inner
Section_1_cell = openmc.Cell(region=Section_1_region)
Section_1_cell.fill = robotarm

#-------------------------------------Inner Copper Section 1 (ICS1)-------------------------------------------------

ICS1_length = Length_Section_1_inner
ICS1_thickness = 2
d1_prime_inner = -120-10
d2_prime_inner = 40
m = ICS1_thickness/(np.cos((np.pi/2)-(np.atan(b_prime/a_prime))))
n=ICS1_length/(np.cos((np.pi/2)-np.atan(b_prime/a_prime)))

Plane_1_ICS1 = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime_inner)
Plane_2_ICS1 = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime_inner-m)
Plane_3_ICS1 = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime_inner)
Plane_4_ICS1 = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime_inner-n)
Plane_5_ICS1 = openmc.ZPlane(z0 = 22)#30
Plane_6_ICS1 = openmc.ZPlane(z0= 21)#14

ICS1_region = -Plane_1_ICS1 & +Plane_2_ICS1 &-Plane_3_ICS1 & +Plane_4_ICS1 & -Plane_5_ICS1 & +Plane_6_ICS1
ICS1_cell = openmc.Cell(region=ICS1_region)
ICS1_cell.fill = robotarm_electronics

#-------------------------------------Robot Arm Section 2-------------------------------------------------

Length_Section_2 = 60
Thickness_Section_2 = 15
Height_from_ground = 90
Plane_1 = openmc.YPlane(y0=Height_from_ground)
Plane_2 = openmc.YPlane(y0=Height_from_ground-Thickness_Section_2)
Plane_3 = openmc.XPlane(x0 = -9)
Plane_4 = openmc.XPlane(x0 = -9+Length_Section_2)
Plane_5 = openmc.ZPlane(z0 = -Thickness_Section_2/2)
Plane_6 = openmc.ZPlane(z0= Thickness_Section_2/2)

Thickness_Section_2_inner =0.5
Plane_1_inner = openmc.YPlane(y0 = Height_from_ground-Thickness_Section_2_inner)
Plane_2_inner = openmc.YPlane(y0 = Height_from_ground-Thickness_Section_2+Thickness_Section_2_inner)
Plane_3_inner = openmc.XPlane(x0 = -9+Thickness_Section_2_inner)
Plane_4_inner = openmc.XPlane(x0 = -9+Length_Section_2-Thickness_Section_2_inner)
Plane_5_inner = openmc.ZPlane(z0 = -Thickness_Section_2/2+Thickness_Section_2_inner)
Plane_6_inner = openmc.ZPlane(z0 = Thickness_Section_2/2-Thickness_Section_2_inner)

Section_2_region_inner = -Plane_1_inner & +Plane_2_inner &+Plane_3_inner & -Plane_4_inner & +Plane_5_inner & -Plane_6_inner & ~Base_region & ~Section_1_region 

Section_2_region = -Plane_1 & +Plane_2 &+Plane_3 & -Plane_4 & +Plane_5 & -Plane_6 & ~Base_region & ~Section_1_region &~Section_2_region_inner
Section_2_cell = openmc.Cell(region=Section_2_region)
Section_2_cell.fill = robotarm

#-------------------------------------Inner Copper Section 2 (ICS2)-------------------------------------------------

Copper_thickness = 2
Plane_1_ICS2 = openmc.YPlane(y0 = Height_from_ground-(Thickness_Section_2/2)+Copper_thickness/2)
Plane_2_ICS2 = openmc.YPlane(y0 = Height_from_ground-(Thickness_Section_2/2)-Copper_thickness/2)
Plane_3_ICS2 = openmc.XPlane(x0 = -9+Thickness_Section_2_inner)
Plane_4_ICS2 = openmc.XPlane(x0 = -9+Length_Section_2-Thickness_Section_2_inner)
Plane_5_ICS2 = openmc.ZPlane(z0 = -Copper_thickness/2)
Plane_6_ICS2 = openmc.ZPlane(z0 = Copper_thickness/2)

ICS2_region = -Plane_1_ICS2 & +Plane_2_ICS2 &+Plane_3_ICS2 & -Plane_4_ICS2 & +Plane_5_ICS2 & -Plane_6_ICS2
ICS2_cell = openmc.Cell(region=ICS2_region)
ICS2_cell.fill = robotarm_electronics


#-------------------------------------Robot Arm Section 3-------------------------------------------------
Length_Section_3 = 30
Thickness_Section_3 = 18
Height_from_ground = 90

Plane_1 = openmc.YPlane(y0=Height_from_ground)
Plane_2 = openmc.YPlane(y0=Height_from_ground-Length_Section_3)
Plane_3 = openmc.XPlane(x0 = -Thickness_Section_3/2)
Plane_4 = openmc.XPlane(x0 = +Thickness_Section_3/2)
Plane_5 = openmc.ZPlane(z0 = -Thickness_Section_2/2-Thickness_Section_3)
Plane_6 = openmc.ZPlane(z0= -Thickness_Section_2/2)


Thickness_Section_3_inner =0.5
Plane_1_inner = openmc.YPlane(y0=Height_from_ground-Thickness_Section_3_inner)
Plane_2_inner = openmc.YPlane(y0=Height_from_ground-Length_Section_3+Thickness_Section_3_inner)
Plane_3_inner = openmc.XPlane(x0 = -Thickness_Section_3/2+Thickness_Section_3_inner)
Plane_4_inner = openmc.XPlane(x0 = +Thickness_Section_3/2-Thickness_Section_3_inner)
Plane_5_inner = openmc.ZPlane(z0 = -Thickness_Section_2/2-Thickness_Section_3+Thickness_Section_3_inner)
Plane_6_inner = openmc.ZPlane(z0= -Thickness_Section_2/2-Thickness_Section_3_inner)

Section_3_region_inner = -Plane_1_inner & +Plane_2_inner &+Plane_3_inner & -Plane_4_inner & +Plane_5_inner & -Plane_6_inner & ~Base_region & ~Section_1_region & ~Section_2_region


Section_3_region = -Plane_1 & +Plane_2 &+Plane_3 & -Plane_4& +Plane_5 & -Plane_6 & ~Base_region & ~Section_1_region & ~Section_2_region &~Section_3_region_inner 
Section_3_cell = openmc.Cell(region=Section_3_region)
Section_3_cell.fill = robotarm

#-------------------------------------Inner Copper Section 3 (ICS3)-------------------------------------------------

Copper_thickness = 2
Plane_1_ICS3 = openmc.YPlane(y0=Height_from_ground-Thickness_Section_3_inner)
Plane_2_ICS3 = openmc.YPlane(y0=Height_from_ground-Length_Section_3+Thickness_Section_3_inner)
Plane_3_ICS3 = openmc.XPlane(x0 = -Copper_thickness/2)
Plane_4_ICS3 = openmc.XPlane(x0 = +Copper_thickness/2)
Plane_5_ICS3 = openmc.ZPlane(z0 = -Thickness_Section_2/2-Thickness_Section_3/2-Copper_thickness/2)
Plane_6_ICS3 = openmc.ZPlane(z0 = -Thickness_Section_2/2-Thickness_Section_3/2+Copper_thickness/2)

ICS3_region = -Plane_1_ICS3 & +Plane_2_ICS3 &+Plane_3_ICS3 & -Plane_4_ICS3 & +Plane_5_ICS3 & -Plane_6_ICS3
ICS3_cell = openmc.Cell(region=ICS3_region)
ICS3_cell.fill = robotarm_electronics


#-------------------------------------Extruder Section-------------------------------------------------
Extender_Section_1_Length =10#18.8 Max
Extender_Section_1_Thickness =0.3
Height_from_ground = 60
Extender_Section_1 = openmc.YCylinder(r=7,x0=0,z0=-Thickness_Section_2/2-Thickness_Section_3/2)
Extender_Section_1_inner = openmc.YCylinder(r=7-Extender_Section_1_Thickness,x0=0,z0=-Thickness_Section_2/2-Thickness_Section_3/2)
Extender_Plane_1 = openmc.YPlane(y0=Height_from_ground)
Extender_Plane_2 = openmc.YPlane(y0=Height_from_ground-Extender_Section_1_Length)

Extender_Section_1_region = -Extender_Section_1 &-Extender_Plane_1 & +Extender_Plane_2 &+Extender_Section_1_inner
Extender_Section_1_cell = openmc.Cell(region=Extender_Section_1_region)
Extender_Section_1_cell.fill = robotarm

Extender_Section_2_Length =10#18.8 Max
Extender_Section_2_Thickness =0.27
Height_from_ground = 60-Extender_Section_1_Length
Extender_Section_2 = openmc.YCylinder(r=5.7,x0=0,z0=-Thickness_Section_2/2-Thickness_Section_3/2)
Extender_Section_2_inner = openmc.YCylinder(r=5.7-Extender_Section_2_Thickness,x0=0,z0=-Thickness_Section_2/2-Thickness_Section_3/2)
Extender_Plane_1 = openmc.YPlane(y0=Height_from_ground)
Extender_Plane_2 = openmc.YPlane(y0=Height_from_ground-Extender_Section_2_Length)

Extender_Section_2_region = -Extender_Section_2 &-Extender_Plane_1 & +Extender_Plane_2 &+Extender_Section_2_inner
Extender_Section_2_cell = openmc.Cell(region=Extender_Section_2_region)
Extender_Section_2_cell.fill = robotarm

Extender_Section_3_Length =10#17.6 Max
Extender_Section_3_Thickness =0.16
Height_from_ground = Height_from_ground-Extender_Section_2_Length
Extender_Section_3 = openmc.YCylinder(r=4.5,x0=0,z0=-Thickness_Section_2/2-Thickness_Section_3/2)
Extender_Section_3_inner = openmc.YCylinder(r=4.5-Extender_Section_3_Thickness,x0=0,z0=-Thickness_Section_2/2-Thickness_Section_3/2)
Extender_Plane_1 = openmc.YPlane(y0=Height_from_ground)
Extender_Plane_2 = openmc.YPlane(y0=Height_from_ground-Extender_Section_3_Length)

Extender_Section_3_region = -Extender_Section_3 &-Extender_Plane_1 & +Extender_Plane_2 &+Extender_Section_3_inner
Extender_Section_3_cell = openmc.Cell(region=Extender_Section_3_region)
Extender_Section_3_cell.fill = robotarm


#-------------------------------------Shielding Plate 1-------------------------------------------------
Thickness = 4
Position_in_xaxis = 90
width = 30
height = 38
plate_thick1=openmc.XPlane(x0 = (-Thickness/2)+Position_in_xaxis)
plate_thick2=openmc.XPlane(x0 = (Thickness/2)+Position_in_xaxis)
plate_height1 = openmc.YPlane(y0 = 0)
plate_height2 = openmc.YPlane(y0 =  height)
plate_width1 = openmc.ZPlane(z0 = -width/2)
plate_width2 = openmc.ZPlane(z0 =  width/2)
plate1_region = +plate_height1 & -plate_height2 & +plate_thick1 & -plate_thick2 & +plate_width1 & -plate_width2
plate1_cell = openmc.Cell(region=plate1_region)
plate1_cell.fill = shielding

#-------------------------------------Shielding Plate 2-------------------------------------------------

Length_Plate_2 = 60
d1_prime = -110
d2_prime = 20
m = Thickness/(np.cos((np.pi/2)-(np.atan(b_prime/a_prime))))
n=Length_Plate_2/(np.cos((np.pi/2)-np.atan(b_prime/a_prime)))

Plane_1 = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime)
Plane_2 = openmc.Plane(a=-a_prime, b=-b_prime, c=0.0, d=d1_prime-m)
Plane_3 = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime)
Plane_4 = openmc.Plane(a=-a_prime, b=b_prime, c=0.0, d=d2_prime-n)
Plane_5 = openmc.ZPlane(z0 = 30)
Plane_6 = openmc.ZPlane(z0 =14)

plate2_region = -Plane_1 & +Plane_2 &-Plane_3 & +Plane_4 & -Plane_5 & +Plane_6
plate2_cell = openmc.Cell(region=plate2_region)
plate2_cell.fill = shielding

#-------------------------------------Shielding Plate 3-------------------------------------------------

plate_thick1 = openmc.XPlane(x0 = -9)
plate_thick2 = openmc.XPlane(x0 = -9+Length_Section_2)
plate_height1 = openmc.YPlane(y0 = 70-Thickness)
plate_height2 = openmc.YPlane(y0 =  70)
plate_width1 = openmc.ZPlane(z0 = -7)
plate_width2 = openmc.ZPlane(z0 =  7)
plate3_region = +plate_height1 & -plate_height2 & +plate_thick1 & -plate_thick2 & +plate_width1 & -plate_width2
plate3_cell = openmc.Cell(region=plate3_region)
plate3_cell.fill = shielding


#-------------------------------------AIR-------------------------------------------------
Room_xmin = openmc.XPlane(x0 =-Plot_Dimension, boundary_type="reflective")
Room_xmax = openmc.XPlane(x0 =+Plot_Dimension, boundary_type="reflective")
Room_zmin = openmc.ZPlane(z0 =-Plot_Dimension, boundary_type="reflective")
Room_zmax = openmc.ZPlane(z0 =+Plot_Dimension, boundary_type="reflective")
Room_ymin = openmc.YPlane(y0 =-100, boundary_type="reflective")
Room_ymax = openmc.YPlane(y0 =+200, boundary_type="reflective")
bounding_area_region = +Room_xmin & -Room_xmax & +Room_ymin & -Room_ymax & +Room_zmin & -Room_zmax & ~body_region & ~capsule_region & ~plate1_region & ~Section_1_region & ~Base_region & ~Section_2_region& ~Section_3_region &~Extender_Section_1_region&~Extender_Section_2_region&~Extender_Section_3_region&~ICB_region&~ICS1_region&~ICS2_region&~ICS3_region&~plate2_region&~plate3_region
bounding_area_cell = openmc.Cell(region=bounding_area_region)
bounding_area_cell.fill = air

universe = openmc.Universe(cells=[capsule_cell, argon_cell, body_cell, plate1_cell,bounding_area_cell,Base_cell,Section_1_cell,Section_2_cell,Section_3_cell,Extender_Section_1_cell,Extender_Section_2_cell,Extender_Section_3_cell,ICB_cell,ICS1_cell,ICS2_cell,ICS3_cell,plate2_cell,plate3_cell])
geometry = openmc.Geometry(universe)
geometry.export_to_xml()

#-------------------------Settings---------------------------------------------------------------
settings = openmc.Settings() # Settings for simulation
settings.run_mode = 'fixed source'
settings.batches = 200
settings.inactive = 10
settings.particles = 500

settings.source = source
settings.export_to_xml()

#-------------------------------------Plot-------------------------------------------------
plot = openmc.Plot()
#plot.basis = "xz" #Top Down
plot.basis = "xy" #Side 
plot.origin = (0, 0, 0)
plot.width = (2*Plot_Dimension, 2*Plot_Dimension) ## Geometry plot sizing
plot.pixels = (3200, 3200) # resolution 
plot.color_by = 'cell'
plot.filename = "geometry_plot"

# Create Plots collection
plots = openmc.Plots([plot])
plots.export_to_xml()  # writes plots.xml

openmc.plot_geometry()  # this will produce geometry_plot.ppm

print("Geometry plot saved as geometry_plot.ppm")

# ---------------------------Tallies------------------------------------------------------
tallies = openmc.Tallies()

mesh = openmc.RegularMesh() ## PLOT SIZE
mesh.dimension = [800, 800]
mesh.lower_left = [-Plot_Dimension, -Plot_Dimension]
mesh.upper_right = [Plot_Dimension, Plot_Dimension]

mesh_filter = openmc.MeshFilter(mesh)

tally = openmc.Tally(name="Energy_deposition")
tally.filters = [mesh_filter]
tally.scores = ["heating"]
tally.particles = ['photon']

tallies.append(tally)
tallies.export_to_xml()
# ---------------------------Tallies Material Absorption-------------------------------------------------

material_filter = openmc.MaterialFilter([shielding]) #Creates filter to look at 1 material

tally_material = openmc.Tally(name="Tungsten Absorption")
tally_material.filters = [material_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()
# ---------------------------Tallies Robot Arm Absorption-------------------------------------------------

cell_filter = openmc.CellFilter([Base_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Base")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([Section_1_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Section 1")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([Section_2_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Section 2")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([Section_3_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Section 3")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([Extender_Section_1_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Extender Section 1")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([Extender_Section_2_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Extender Section 2")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([Extender_Section_3_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Extender Section 3")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([ICB_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Inner Copper Base")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([ICS1_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Inner Copper Section 1")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()
cell_filter = openmc.CellFilter([ICS2_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Inner Copper Section 2")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()

cell_filter = openmc.CellFilter([ICS3_cell]) 

tally_material = openmc.Tally(name="Robot Arm Absorption Inner Copper Section 3")
tally_material.filters = [cell_filter]
tally_material.scores = ["heating"]
tally_material.particles = ["photon"]

tallies.append(tally_material)
tallies.export_to_xml()



### ----------------------Run OpenMC---------------------------------------------------------
subprocess.run(["openmc"], check=True)
##-----------------------2D Plots-----------------------------------------------------------


sp = openmc.StatePoint('statepoint.200.h5')
tally = sp.get_tally(name="Energy_deposition")

mean = tally.get_values(scores=["heating"]).reshape(mesh.dimension)
plt.imshow(mean, origin='lower', extent=[-Plot_Dimension, Plot_Dimension, -Plot_Dimension, Plot_Dimension],
           norm=LogNorm(vmin=1e-6, vmax=mean.max()))#Log Plot Version  Dimensions(Left,Right,Bottom,Top)
#plt.imshow(mean, origin='lower', extent=[-10, 10, -10, 10])#Linear Plot
plt.title("Energy deposition per source particle per mesh voxel (eV)")
plt.xlabel("x [cm]")
plt.xlim(-100,Plot_Dimension)
plt.ylim(-100,200)
plt.ylabel("y [cm]")
#plt.scale("log")
plt.colorbar(label="Energy deposited per source particle per voxel (eV)")
plt.tight_layout()
plt.savefig("absorption_plot.png", dpi=300)
plt.close()
print("Saved absorption plot as absorption_plot.png")
#---------------------------Function for conversion of absorption data-------------------------------------------------

def convert_heating_to_J_per_hour(heating_eV_per_source,mass):
    
    # Activity in decays per second
    activity_Bq = Activity * 3.7e7  # mCi to Bq

    # Ir-192 photons per second
    photons_per_sec = activity_Bq *2.2

    # Energy deposition
    energy_J_per_sec = (
        heating_eV_per_source
        * photons_per_sec
        * 1.602176634e-19  # J/eV
    )
    energy_J_per_sec * 3600  # J/hour
    Gray_hour = (energy_J_per_sec * 3600)/mass #90kg weight of robot
    return Gray_hour  # Gy/hour


# ---------------------------Absorption Data-------------------------------------------------

Absorption_Data_Robotarm = []

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Base")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 40

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Base: {Gray_hour} Gy/hour")


sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Section 1")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 10

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Section 1: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Section 2")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 5

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Section 2: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Section 3")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 4

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Section 3: {Gray_hour} Gy/hour")


# ---------------------------Absorption Data Extruder-------------------------------------------------
sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Extender Section 1")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 1

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Extender Section 1: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Extender Section 2")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 1

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Extender Section 2: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Extender Section 3")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 1

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_Robotarm.append(Gray_hour)

print(f"Energy deposited in Robot Arm Extender Section 3: {Gray_hour} Gy/hour")

# ---------------------------Absorption Data Copper-------------------------------------------------

Absorption_Data_RobotElec = []
sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Inner Copper Base")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 3.83

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_RobotElec.append(Gray_hour)

print(f"Energy deposited in Robot Arm Absorption Inner Copper Base: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Inner Copper Section 1")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 3.1

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_RobotElec.append(Gray_hour)

print(f"Energy deposited in Robot Arm Absorption Inner Copper Section 1: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Inner Copper Section 2")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 2.1

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_RobotElec.append(Gray_hour)

print(f"Energy deposited in Robot Arm Absorption Inner Copper Section 2: {Gray_hour} Gy/hour")

sp = openmc.StatePoint('statepoint.200.h5')
tally_arm = sp.get_tally(name="Robot Arm Absorption Inner Copper Section 3")

heating_value = tally_arm.mean.flatten()[0]  # eV / source particle
mass = 1

Gray_hour = convert_heating_to_J_per_hour(heating_value,mass)
Absorption_Data_RobotElec.append(Gray_hour)

print(f"Energy deposited in Robot Arm Absorption Inner Copper Section 3: {Gray_hour} Gy/hour")


# ---------------------------Lifespan Calculations-------------------------------------------------
Number_of_sources = 20
Opperation_Length = 0.5#In hours
Safety_Factor = 0.5

Absorption_Data_Robotarm.sort(reverse=True)
Absorption_Data_RobotElec.sort(reverse=True)

Robotarm_max = Absorption_Data_Robotarm[0]
RobotElec_max =  Absorption_Data_RobotElec[0]


LifeSpan_arm = (150000*Safety_Factor) / (Robotarm_max * Number_of_sources) #Number of hours until 150kGy Exposure
LifeSpan_Elec = (600*Safety_Factor) / (RobotElec_max * Number_of_sources) #Number of hours until 600Gy Exposure

TotalOperations_arm = LifeSpan_arm/Opperation_Length
TotalOperations_Elec = LifeSpan_Elec/Opperation_Length

print(f"Total length of exposure is {LifeSpan_arm:.1f} hours, meaning {TotalOperations_arm:.1f} Operations before unsafe")
print(f"Total length of exposure is {LifeSpan_Elec:.1f} hours, meaning {TotalOperations_Elec:.1f} Operations before unsafe") 


    
