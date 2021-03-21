import numpy as np
from mpi4py import MPI

import openmdao.api as om
from mphys.multipoint import Multipoint
from mphys.mphys_vlm import *

comm = MPI.COMM_WORLD

class Top(om.Group):
    def setup(self):
        # VLM options

        aero_options = {
            'mesh_file':'../input_files/debug_VLM.dat',
            'mach':0.85,
            'aoa':1*np.pi/180.,
            'q_inf':25000.,
            'vel':178.,
            'mu':3.5E-5,
        }

        # VLM mesh read
        def read_VLM_mesh(mesh):
            f=open(mesh, "r")
            contents = f.read().split()

            a = [i for i in contents if 'NODES' in i][0]
            N_nodes = int(a[a.find("=")+1:a.find(",")])
            a = [i for i in contents if 'ELEMENTS' in i][0]
            N_elements = int(a[a.find("=")+1:a.find(",")])

            a = np.array(contents[16:16+N_nodes*3],'float')
            X = a[0:N_nodes*3:3]
            Y = a[1:N_nodes*3:3]
            Z = a[2:N_nodes*3:3]
            a = np.array(contents[16+N_nodes*3:None],'int')
            quad = np.reshape(a,[N_elements,4])

            xa = np.c_[X,Y,Z].flatten(order='C')

            f.close()

            return N_nodes, N_elements, xa, quad

        aero_options['N_nodes'], aero_options['N_elements'], aero_options['x_aero0'], aero_options['quad'] = read_VLM_mesh(aero_options['mesh_file'])
        self.aero_options = aero_options

        dvs = self.add_subsystem('dvs',om.IndepVarComp(), promotes=['*'])

        vlm_builder = VlmBuilder(aero_options)
        mp = self.add_subsystem(
            'mp_group',
            Multipoint(aero_builder = vlm_builder)
        )

        mp.mphys_add_scenario('s0')

    def configure(self):
        self.dvs.add_output('aoa', self.aero_options['aoa'], units='rad')
        self.dvs.add_output('u_aero', np.zeros_like(self.aero_options['x_aero0']))
        self.connect('aoa',['mp_group.s0.solver_group.aero.aoa'])
        self.connect('u_aero','mp_group.s0.solver_group.aero.u_aero')

## openmdao setup

connection_srcs = {}
prob = om.Problem()

prob.model = Top()

prob.setup(force_alloc_complex=True)
prob.run_model()
prob.check_partials(method='cs',compact_print=True)