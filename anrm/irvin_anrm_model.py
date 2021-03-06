from pysb import *
from pysb.util import alias_model_components
from earm import shared

from earm import lopez_modules as lopez
from earm import albeck_modules as albeck
import irvin_modules_v6 as irvin
import merge

# -----Monomers-----
def compile_monomers():
    Model('m')
    # From irvin_modules
    irvin.TNFa_to_ComplexI_Monomers()
    irvin.ComplexII_to_Bid_Monomers()
    irvin.NFkB_Activation_and_Signaling_monomers()
    irvin.Bid_Hypothesis_monomers()
    irvin.Momomers_zVad_to_C8()
    
    # From lopez_modules
    lopez.momp_monomers()
    
    # From albeck_modules
    albeck.apaf1_to_parp_monomers()
    return m.monomers

revised_monomers = {'Bid' :(['bf', 'state'], {'state':['U', 'T', 'M', 'po4']}),
    'C6'  :(['bf1','bf2', 'state'], {'state':['pro', 'A']}),
    'PARP':(['bf', 'state'], {'state':['U', 'C', 'A']}),
    'C3': (['bf', 'state'], {'state':['pro', 'A', 'ub', 'I']})}

monomer_edits = merge.Edit_Monomers(compile_monomers(), revised_monomers)
merged_monomers = monomer_edits.merged_monomers

Model('model')
model.monomers = merged_monomers

irvin.TNFa_to_ComplexI_Initials()
irvin.TNFa_to_ComplexI()
irvin.CompI_TRADD_RIP1_Dissociation()
"""Hypothesis 1: FADD transiently localizes to TNFR1 to retrieve RIP1
    Hypothesis 2: FADD replaces TRADD in TRADD:RIP1
    Hypothesis 3: FADD binds TRADD in TRADD:RIP1"""
irvin.CompII_Hypothesis_1_FADD_CompI_interaction()
irvin.CompII_Hypothesis_2_FADD_displaces_TRADD()
irvin.CompII_Hypothesis_3_FADD_binds_TRADD()
irvin.ComplexII_to_Bid_Initials()
irvin.ComplexIIa_Assembly()
irvin.ComplexIIb_to_MLKL()
irvin.RIP1_truncation_ComplexII()
irvin.C8_catalyzed_truncations()
irvin.NFkB_Activation_and_Signaling_Initials()
irvin.NFkB_Activation_and_Signaling()

irvin.Bid_Hypothesis_initials()
"""Hypothesis 0: Bid-po4 does not occur
    Hypothesis 1: Bid-po4 recruits proC8 and cFlip_L and mediates RIP1 and CYLD truncation."""
irvin.Bid_Hypothesis_2() #Bid mediated inhibition of necrosis (revised hypothesis)
irvin.Bid_proC8_cleaves_substrates() #Bid mediated inhibition of necrosis (revised hypothesis)

irvin.C3_inhibits_MLKL()
irvin.Initials_zVad_to_C8()
irvin.zVad_to_C8()
irvin.observables()

# From lopez_modules
lopez.declare_initial_conditions()
lopez.translocate_tBid_Bax_BclxL()
lopez.tBid_activates_Bax_and_Bak()
lopez.tBid_binds_all_anti_apoptotics()
lopez.sensitizers_bind_anti_apoptotics()
lopez.effectors_bind_anti_apoptotics()
lopez.lopez_pore_formation(do_pore_transport=True)

#From irvin_modules
irvin.pore_to_parp()


 

