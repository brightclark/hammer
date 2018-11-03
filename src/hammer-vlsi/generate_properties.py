#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  generate_properties.py
#  
#  Copyright 2017 Edward Wang <edward.c.wang@compdigitec.com>
#  Helper script to generate properties for hammer-vlsi tool classes.

from collections import namedtuple
import sys

import os
import re

InterfaceVar = namedtuple("InterfaceVar", 'name type desc')

Interface = namedtuple("Interface", 'module filename inputs outputs')

def isinstance_check(t: str) -> str:
    return "isinstance(value, {t})".format(t=t)

def generate_from_list(template: str, lst):
    def format_var(var):
        attr_error_logic = """raise ValueError("Nothing set for the {var_desc} yet")"""

        if var.type.startswith("Iterable"):
            var_type_instance_check = isinstance_check("Iterable")
        elif var.type.startswith("List"):
            var_type_instance_check = isinstance_check("List")
        elif var.type.startswith("Optional"):
            m = re.search(r"Optional\[(\S+)\]", var.type)
            subtype = str(m.group(1))
            var_type_instance_check = isinstance_check(subtype) + " or (value is None)"
            attr_error_logic = "return None"
        else:
            var_type_instance_check = isinstance_check(var.type)

        t = template.replace("[[attr_error_logic]]", attr_error_logic)

        return t.format(var_name=var.name, var_type=var.type, var_desc=var.desc,
                               var_type_instance_check=var_type_instance_check)
    return map(format_var, lst)

def generate_interface(interface: Interface):
    template = """
    @property
    def {var_name}(self) -> {var_type}:
        \"""
        Get the {var_desc}.

        :return: The {var_desc}.
        \"""
        try:
            return self.attr_getter("_{var_name}", None)
        except AttributeError:
            [[attr_error_logic]]

    @{var_name}.setter
    def {var_name}(self, value: {var_type}) -> None:
        \"""Set the {var_desc}.\"""
        if not ({var_type_instance_check}):
            raise TypeError("{var_name} must be a {var_type}")
        self.attr_setter("_{var_name}", value)
"""
    start_key = "    ### Generated interface %s ###" % (interface.module)
    end_key =   "    ### END Generated interface %s ###" % (interface.module)

    output = []
    output.append(start_key)
    output.append("    ### DO NOT MODIFY THIS CODE, EDIT %s INSTEAD ###" % (os.path.basename(__file__)))
    output.append("    ### Inputs ###")
    output.extend(generate_from_list(template, interface.inputs))
    output.append("")
    output.append("    ### Outputs ###")
    output.extend(generate_from_list(template, interface.outputs))
    output.append(end_key)

    filename = os.path.join(os.path.dirname(__file__), interface.filename)

    contents = ""
    with open(filename, "r") as f:
        contents = f.read()

    with open(filename, "w") as f:
        f.write(re.sub(re.escape(start_key) + ".*" + re.escape(end_key), "\n".join(output), contents, flags=re.MULTILINE | re.DOTALL))


def main(args):
    HammerSynthesisTool = Interface(module="HammerSynthesisTool",
        filename="hammer_vlsi/hammer_vlsi_impl.py",
        inputs=[
            InterfaceVar("input_files", "List[str]", "input collection of source RTL files (e.g. *.v)"),
            InterfaceVar("top_module", "str", "top-level module")
        ],
        outputs=[
            InterfaceVar("output_files", "List[str]", "output collection of mapped (post-synthesis) RTL files"),
            InterfaceVar("output_sdc", "str", "(optional) output post-synthesis SDC constraints file")
            # TODO: model CAD junk
        ]
    )

    HammerPlaceAndRouteTool = Interface(module="HammerPlaceAndRouteTool",
        filename="hammer_vlsi/hammer_vlsi_impl.py",
        inputs=[
            InterfaceVar("input_files", "List[str]", "input post-synthesis netlist files"),
            InterfaceVar("top_module", "str", "top RTL module"),
            InterfaceVar("post_synth_sdc", "Optional[str]", "(optional) input post-synthesis SDC constraint file")
        ],
        outputs=[
            # TODO: model more CAD junk

            # e.g. par-rundir/TopModuleILMDir/mmmc/ilm_data/TopModule. Has a bunch of files TopModule_postRoute*
            InterfaceVar("output_ilms", "List[ILMStruct]", "(optional) output ILM information for hierarchical mode"),
            InterfaceVar("output_gds", "str", "path to the output GDS file"),
            InterfaceVar("output_netlist", "str", "path to the output netlist file"),
            InterfaceVar("power_nets", "List[str]", "list of all the power nets in the design"),
            InterfaceVar("ground_nets", "List[str]", "list of all the ground nets in the design"),
            InterfaceVar("hcells_list", "List[str]", "list of cells to explicitly map hierarchically in LVS")

            # TODO: add individual parts of the ILM (e.g. verilog, sdc, spef, etc) for cross-tool compatibility?
        ]
    )

    HammerDRCTool = Interface(module="HammerDRCTool",
        filename="hammer_vlsi/hammer_vlsi_impl.py",
        inputs=[
            InterfaceVar("layout_file", "str", "path to the input layout file (e.g. a *.gds)"),
            InterfaceVar("top_module", "str", "top RTL module")
        ],
        outputs=[]
    )

    HammerLVSTool = Interface(module="HammerLVSTool",
        filename="hammer_vlsi/hammer_vlsi_impl.py",
        inputs=[
            InterfaceVar("layout_file", "str", "path to the input layout file (e.g. a *.gds)"),
            InterfaceVar("schematic_files", "List[str]", "path to the input SPICE or Verilog schematic files (e.g. *.v or *.spi)"),
            InterfaceVar("top_module", "str", "top RTL module"),
            InterfaceVar("power_nets", "List[str]", "list of all the power nets in the design"),
            InterfaceVar("ground_nets", "List[str]", "list of all the ground nets in the design"),
            InterfaceVar("hcells_list", "List[str]", "list of cells to explicitly map hierarchically in LVS")
        ],
        outputs=[]
    )

    generate_interface(HammerSynthesisTool)
    generate_interface(HammerPlaceAndRouteTool)
    generate_interface(HammerDRCTool)
    generate_interface(HammerLVSTool)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
