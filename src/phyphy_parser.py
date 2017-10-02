"""
    Parse HyPhy JSON output
"""

import os
import re
import json
import pyvolve
from copy import deepcopy

class JSONFields():
    """
        Define the fields used in JSONs. Essentially the terms.json namespace terms.
    """
    
    def __init__(self):
        
        self.input                = "input"
        self.input_info           = "info"
        self.input_filename       = "file name"
        self.input_sites          = "number of sites"
        self.input_sequences      = "number of sequences"
        self.input_npartitions    = "partition count"
        self.input_trees          = "trees"
        
        self.rate_distributions   = "Rate Distributions"
        
        self.analysis_description      = "analysis"
        self.analysis_description_info = "info"
        
        self.relative_site_rates = "Relative site rate estimates"
        self.UB                  = "UB"
        self.LB                  = "LB"

        self.tested = "tested"
        self.MLE                       = "MLE"
        self.MLE_headers               = "headers"
        self.MLE_content               = "content"
        
        self.model_fits   = "fits"
        self.log_likelihood =  "Log Likelihood"
        self.aicc           = "AIC-c"
        self.estimated_parameters = "estimated parameters"
        self.frequencies = "Equilibrium frequencies"
        
        self.branch_attributes   = "branch attributes"
        self.attributes          = "attributes"
        self.attribute_type      ="attribute type"
        self.timers = "timers"
    


"""
        // For any json
        json                  = "json";
        analysis              = "analysis";
        input                 = "input";
        file                  = "file name";
        sequences             = "number of sequences";
        sites                 = "number of sites";
        fits                  = "fits";
        timers                = "timers";
        trees                 = "trees";
        MLE                   = "MLE";
        parameters            = "estimated parameters";
        PMID                  = "PMID";
 //       PMCID                 = "PMCID";
        test_results          = "test results";
        tree_string           = "tree";
        tree_length           = "tree length";
        rate_distribution     = "Rate Distributions";
        log_likelihood        = "Log Likelihood";
        AICc                  = "AIC-c";
        global_mg94xrev       = "Global MG94xREV";
        mg94xrev_sep_rates    = "MG94xREV with separate rates for branch sets";
        nucleotide_gtr        = "Nucleotide GTR";
        frequencies           = "Equilibrium frequencies";
        model                 = "model"; // TODO: change string to "model name"
       // global                = "Global model fit"; // Defined at the top of file
        attribute             = "attributes";
        display_order         = "display order";
        attribute_type        = "attribute type";
        node_label           = "node label";
        branch_label          = "branch label";
        branch_attributes     = "branch attributes";
        branch_annotations    = "branch annotations";
        annotation_tag        = "annotation tag";
        branch_lengths        = "branch lengths";
  //      background            = "background";

        headers               = "headers";
        content               = "content";
        partition_count       = "partition count";
        partitions            = "data partitions";

        tested                = "tested";
        uncorrected_pvalue    = "Uncorrected P-value";
        corrected_pvalue      = "Corrected P-value";
        pvalue_threshold      = "P-value threshold";
        relative_site_rates   = "Relative site rate estimates";
      //  site_log_likelihood   = "site log likelihood";
     //   evidence_ratios       = "evidence ratios";
        options               = "options";
        runtime               = "runtime";
        version               = "version";
        convergence_failures  = "convergence failures";
        omega_ratio           = "omega";
        proportion            = "proportion";
        positive              = "positive test results";
    }
"""
        

class HyPhyParser():
    
    def __init__(self, json_path, analysis = None):
        """
            Parse JSON output.
        """
        self.fields = JSONFields()
        self.genetics = pyvolve.Genetics()
        self.json_path = json_path
        assert(os.path.exists(self.json_path)), "\nERROR: JSON file provided does not exist."
        
        ## Parse to dictionary
        self._unpack_json()
        
        ## Determine analysis method
        self.analysis = analysis
        if self.analysis is None:
            self._determine_analysis_from_json()
            
        ## Count partitions, which is generally useful to have
        self._count_partitions()

    ############################## PRIVATE FUNCTIONS #################################### 
    def _unpack_json(self):
        """
            Unpack JSON into dictionary
        """ 
        with open (self.json_path, "rU") as f:
            self.json = json.load(f)
            
    
    def _determine_analysis_from_json(self):

        analyis_matches = ["FEL", "SLAC", "MEME", "FUBAR", "ABSREL", "RELAX", "BUSTED"]
        json_info = self.json[ self.fields.analysis_description ][ self.fields.analysis_description_info ].upper()
        
        for name in analyis_matches:
        
            find_analysis = re.search(name.upper(), json_info)
            if find_analysis is not None:
                self.analysis = name
                break
        
        assert(self.analysis is not None), "\nERROR: Could not determine analysis from JSON. Please ensure that the JSON is correctly formatted."



    def _count_partitions(self):
        """
            Define self.npartitions
        """
        if self.analysis == "relative rates":
            self.npartitions = 1
        else:
            self.npartitions = int(self.json[ self.fields.input ][ self.fields.input_npartitions ])
   


    def _extract_slac_sitetable(self, raw, slac_by, slac_ancestral_type):
        """
            Extract the specific SLAC tables of interest
        """
        final = {}
        for x in range(self.npartitions):
            part = raw[str(x)]
            subset = part[slac_by][slac_ancestral_type]
            final[str(x)] = subset
        return final          
            
        


    def _parse_sitemethod_to_csv(self, delim, slac_by = "by-site", slac_ancestral_type = "AVERAGED"):
        """
            Extract a CSV from a site-level method JSON, including FEL, SLAC, MEME, FUBAR.
        """
        site_block =  self.json[ self.fields.MLE ]
        raw_header = site_block[ self.fields.MLE_headers ]
        raw_content = site_block[ self.fields.MLE_content]
        if self.analysis == "SLAC":
            raw_content = self._extract_slac_sitetable(raw_content, slac_by, slac_ancestral_type)
            
        final_header = "site,"+delim.join( [x[0].replace(" ","_") for x in raw_header] )
        if self.npartitions > 1:
            final_header = "partition," + final_header
        
        site_count = 1
        final_content = ""
        for part in raw_content:
            for row in raw_content[part]:
                row = "\n" + str(site_count) + delim + delim.join(str(x) for x in row)
                if self.npartitions > 1:
                    row = str(part) + delim + row
                final_content += row
                site_count += 1
        
        with open(self.csv, "w") as f:
            f.write(final_header + final_content)



    def _parse_absrel_to_csv(self, delim):
        """
            Create CSV from aBSREL results:
                Node name, Baseline MG94 omega, Number of inferred rate classes, Tested (bool), Proportion of selected sites, LRT, uncorrected P, bonferroni-holm P
        """
        
        header = delim.join( ["node", "baseline_omega", "number_rate_classes", "tested", "prop_sites_selected", "LRT", "uncorrected_P", "corrected_P"] )
        attr = self.json[ self.fields.branch_attributes ]["0"] ## Only allowed single partition for ABSREL
        node_names = list( self.json[ self.fields.branch_attributes ]["0"].keys())  
        
        full_rows = ""
        for node in node_names:
            
            try:
                d = attr[str(node)]
            except:
                raise KeyError("\nERROR: Unable to parse JSON.")
            rates = d[self.fields.rate_distributions]
            if len(rates) > 1:
                for pair in rates:
                    if pair[0] > 1.:
                        prop = str(pair[1])
                        break
            else:
                prop = "0"
            
            if d["LRT"] == 1 and d["Uncorrected P-value"] ==  1 and d["Corrected P-value"] == 1:
                run = "0"
            else:
                run  = "1"
                
            row = "\n" + delim.join([node, 
                                    str(d["Baseline MG94xREV omega ratio"]), 
                                    str(d["Rate classes"]), 
                                    run,
                                    prop,
                                    str(d["LRT"]), 
                                    str(d["Uncorrected P-value"]), 
                                    str(d["Corrected P-value"]) ])
            full_rows += row
        
        with open(self.csv, "w") as f:
            f.write(header + full_rows)




    def _parse_relrates_to_csv(self, delim):
        """
            Parse AA or nucleotide relative rates to CSV:
                site, rate, lower95, upper95
        """
        
        header = delim.join( ["site", "rate", "lower_95_bound", "upper_95_bound"] )
        attr = self.json[ self.fields.relative_site_rates ]
        nsites = self.json[ self.fields.input ][ self.fields.input_sites ]
        
        full_rows = ""
        for i in range(nsites):
            
            site = str(i+1)
            row = "\n" + delim.join( [ site, str(attr[site][self.fields.MLE]), str(attr[site][self.fields.LB]), str(attr[site][self.fields.UB]) ])
            full_rows += row
         
        with open(self.csv, "w") as f:
            f.write(header + full_rows)
       
        
        









     
    def _reform_rate_phrase(self, phrase):
        """
            Convert rate phrase to simpler key, i.e. A->C returns key "AC"
        """
        find = re.search(u"Substitution rate from [\w-]+ (\w) to [\w-]+ (\w)", phrase)
        if find:
            source = find.group(1).upper()
            target = find.group(2).upper()
        
            return source + target
        else:
            raise AssertionError("ERROR: Bad rate reform.")



    def _replace_tree_info(self, tree, node, newvalue):
        """
            Replace <stuff> in :Node<stuff> in tree at given node with the newvalue, for attribute mapping.
        """
        return re.sub(node + ":[\.\de-]+?([,\)])", node + ":" + newvalue + "\\1", tree)
        


    ############################################## PUBLIC FUNCTIONS ################################################### 


    ################################################ MODEL FITS #######################################################
    def extract_model_names(self):
        """
            Get the list of fitted models.
        """

        self.fitted_models = list( self.json[ self.fields.model_fits ].keys())
        return self.fitted_models


    def extract_model_component(self, model_name, component):
        """
            For a given fitted model that appears in "fits", return a component of the fit.
        """
        try:
            model_fit = self.json[ self.fields.model_fits ][ model_name ]
        except:
            raise KeyError("\nERROR: Invalid model name.")
            
        try:
            component = model_fit[component]
        except: 
            raise KeyError("\nERROR: Invalid model component.")
            
        return component


    def extract_model_logl(self, model_name):
        """
            Return log likelihood for a given model that appears in "fits".
        """
        return self.extract_model_component(model_name, self.fields.log_likelihood)


    def extract_model_estimated_parameters(self, model_name):
        """
            Return estimated parameters for a given model that appears in "fits".
        """
        return self.extract_model_component(model_name, self.fields.estimated_parameters)


    def extract_model_aicc(self, model_name):
        """
            Return AICc for a given model that appears in "fits".
        """
        return self.extract_model_component(model_name, self.fields.AICc)


    def extract_model_rate_distributions(self, model_name):
        """
            Return rate distributions, as a reformatted dictionary, for a given model that appears in "fits".
            
            NOTE: Currently assumes dS = 1 for all initial MG94xREV fits, as in the current HyPhy implementation (True in <=2.3.4).
        """
        rawrates = self.extract_model_component(model_name, self.fields.rate_distributions)
        rates = {}
        
        if model_name == "Nucleotide GTR": ### TODO: dehardcode
            for k,v in rawrates.items():
                rates[ self._reform_rate_phrase(k) ] = v       
        
        elif "MG94xREV" in model_name:
            if self.analysis == "ABSREL":
                rates = rawrates["Per-branch omega"]   ### TODO: dehardcode 
            else:
                rates = {}
                for k,v in rawrates.items():
                    find = re.search(u"non-synonymous/synonymous rate ratio for \*(\w+)\*", k) ### TODO: dehardcode 
                    if find:
                        rates[find.group(1)] = {"omega": v[0][0], "proportion": 1.0}
                    else:
                        rates["omega"] = v[0][0]  
        else:
            rates = rawrates
        return rates



    def extract_model_frequencies(self, model_name, as_dict = False):
        """
            Return log likelihood for a given model that appears in "fits".
            With "as_dict = True", returns frequencies as dictionary

        """
        fraw = self.extract_model_component(model_name, self.fields.frequencies)
        f = [float(x[0]) for x in fraw]
        
        if as_dict:
            codes = {4: self.genetics.nucleotides, 20: self.genetics.amino_acids, 61: self.genetics.codons}
            try:
                fdict = dict(zip( codes[len(f)], f))
            except:
                raise AssertionError("\nERROR: Unknown frequencies found in JSON. Please report bug to github.com/veg/hyphy/issues.")            
            return fdict
        else:
            return f   
    ###################################################################################################################
    
    
     
    ################################################ BRANCH SETS ######################################################
  
    def extract_branch_sets(self, by_set = False):
        """
            Return branch set designations for all nodes.
            Default, returns as is in JSON where nodes are keys
            If by_set if True, swap out so keys are branch sets and values are list of nodes

            NOTE: Assumes that all partitions share the same branch sets (True in <=2.3.4)
        """
        try:
            branch_sets = self.json[ self.fields.tested ]["0"]
        except:
            raise KeyError("\nERROR: Provided JSON has no branch set designations")
            
        if not by_set:
            return branch_sets
        else:
            branch_sets2 = {}
            for k,v in branch_sets.items():
                if v in branch_sets2:
                    branch_sets2[v].append(k)
                else:
                    branch_sets2[v] = [k]
            return branch_sets2
     ###################################################################################################################



    ######################################## TREE WITH VARIOUS ATTRIBUTES ##############################################
    
    def extract_input_tree(self, partition = None):
        """
            Return the inputted newick phylogeny.
            If there are multiple partitions (and therefore multiple trees), default returns a *list* of trees. 
            If partition = [some integer], that partition's tree only will be returned. NOTE: PARTITION STARTS FROM 0.
        """
        tree_field = self.json[ self.fields.input ][ self.fields.input_trees ]
        if self.npartitions == 1:
            self.input_tree = str(tree_field["0"]) + ";"
            return self.input_tree
        
        else:
            self.input_tree = []
            for i in range(len(tree_field)):
                self.input_tree.append( str(tree_field[str(i)]) + ";" )
        
            if partition is not None:
                try:
                    return self.input_tree[partition]
                except:
                    raise KeyError("\nERROR: Partition not found. Note that partitions are enumerated starting from 0.")
            else:
                return self.input_tree

    
    def reveal_branch_attributes(self):
        """
            Return a dictionary of all the attributes and their attribute type (node label or branch label)
        """
        attributes_info = self.json[ self.fields.branch_attributes ][ self.fields.attributes ]
        #attributes_list = [str(x) for x in self.json[ self.fields.branch_attributes ][ self.fields.attributes ].keys()]
        self.attribute_names = {}
        for x in attributes_info:
            if x == "display order":
                continue
            else:
                self.attribute_names[str(x)] = str(attributes_info[x][self.fields.attribute_type])
        return self.attribute_names
        

        
    
    def extract_branch_attribute(self, attribute_name, partition = None, map = False):
        """
            Return dictionary of attributes for given attribute, where keys are nodes and values are attributes.
            If there are multiple partitions, default returns a dictionary with all partitions. 
            If partition = [some integer], only the attribute for the given partition will be returned. NOTE: PARTITION STARTS FROM 0.            
        """
        self.reveal_branch_attributes() ## Needed to create self.attribute_names
        assert(attribute_name in self.attribute_names), "\nERROR: Specified attribute does not exist in JSON."
        
        attr_dict = {}
        for x in range(self.npartitions):
            partition_attributes = self.json[ self.fields.branch_attributes ][str(x)]           
            for node in partition_attributes:
                attribute_value = str( partition_attributes[node][attribute_name] )
                attr_dict[str(node)] = attribute_value
        
        if partition is not None:
            try:
                return attr_dict[str(partition)]
            except:
                raise KeyError("\nERROR: Partition not found. Note that partitions are enumerated starting from 0.")
        else:
            return attr_dict
        
        
        
        
        
    def map_branch_attribute(self, attribute_name, partition = None):
        """
            Return an attribute mapped onto the newick phylogeny.
            If there are multiple partitions, default returns a list of mapped for all partitions. 
            If partition = [some integer], only the attribute for the given partition will be returned. NOTE: PARTITION STARTS FROM 0.            
        """
        assert(attribute_name != self.fields.rate_distributions), "\nERROR: Cannot map rate distributions onto a tree."
                
        attr_dict = self.extract_branch_attribute(attribute_name)
        self.extract_input_tree()       ## Needed to grab input tree (grab all)
        ptree = deepcopy( self.input_tree )
        
        if self.npartitions == 1:
            for node in attr_dict:
                ptree = self._replace_tree_info( ptree, node, str(attr_dict[node]) )
            return ptree
        
        else:
            many_trees = []
            for ptree in self.input_tree:
                for node in attr_dict:
                    ptree = self._replace_tree_info( ptree, node, str(attr_dict[node]) )
                many_trees.append(ptree)
        
        if partition is not None:
            try:
                return many_trees[partition]
            except:
                raise KeyError("\nERROR: Partition not found. Note that partitions are enumerated starting from 0.")
        else:
            return many_trees
    
 
    def extract_model_tree(self, model, partition = None):
        """
            Return newick phylogeny fitted to a certain model, i.e. with branch lengths optimized for specified model.
            This is just a special case of map_branch_attribute.
        """
        return self.map_branch_attribute(model, partition = partition)
        
           
    ############################################################################################################################

    def extract_csv(self, csv, delim = ",", slac_by = "by-site", slac_ancestral_type = "AVERAGED"):
        """
            Extract results to a CSV. Currently only for SLAC, MEME, FEL, FUBAR, aBSREL, and relative rates. Other analyses do not lend well to CSV.
            
        """       
        
        self.csv = csv

        ### Standard site output ###
        if self.analysis in ["SLAC", "MEME", "FEL", "FUBAR"]:
            assert(slac_by in ["by-site", "by-branch"]), "\nERROR: Argument `slac_by` must be either 'by-site' or 'by-branch'."
            assert(slac_ancestral_type in ["AVERAGED", "RESOLVED"]), "\nERROR: Argument `slac_ancestral_type` must be either 'AVERAGED' or 'RESOLVED'."
            self._parse_sitemethod_to_csv(delim)
            

        ### aBSREL ###
        elif self.analysis == "ABSREL":
            self._parse_absrel_to_csv(delim)
        

        ## TODO: should be parsed out somehow ##
        elif self.analysis == "relative rates":
            self._parse_relrates_to_csv(delim)
            
        else:
            print("\nContent from provided analysis is not convertable to CSV.")
        
        
        
        
      ############################################################################################################################
      
    def extract_timers(self):
        """
            Extract dictionary of timers, with display order removed
        """
        raw = self.json[self.fields.timers]
        final = {}
        for step in raw:
            del raw[step]["order"]
            for k,v in raw[step].items():
                final[str(step)] = float(v)
        return final
        
        
          
        
        
        
        
                

