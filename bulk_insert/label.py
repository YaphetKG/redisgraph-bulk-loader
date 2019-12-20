import sys
import click
from entity_file import EntityFile
from configs import Configs
from exceptions import SchemaError
import module_vars
from schema import Type
from schema import convert_schema_type


# Handler class for processing label csv files.
class Label(EntityFile):
    def __init__(self, infile):
        super(Label, self).__init__(infile)
        # Verify that exactly one field is labeled ID.
        if self.types.count(Type.ID) != 1:
            raise SchemaError("Node file '%s' should have exactly one ID column."
                              % (infile.name))

    def process_entities(self):
        entities_created = 0
        with click.progressbar(self.reader, length=self.entities_count, label=self.entity_str) as reader:
            for row in reader:
                self.validate_row(row)
                # Add identifier->ID pair to dictionary if we are building relations
                if module_vars.NODE_DICT is not None:
                    if row[0] in module_vars.NODE_DICT:
                        sys.stderr.write("Node identifier '%s' was used multiple times - second occurrence at %s:%d\n"
                                         % (row[0], self.infile.name, self.reader.line_num))
                        if module_vars.CONFIGS.skip_invalid_nodes is False:
                            sys.exit(1)
                    module_vars.NODE_DICT[row[0]] = module_vars.TOP_NODE_ID
                    module_vars.TOP_NODE_ID += 1
                row_binary = self.pack_props(row)
                row_binary_len = len(row_binary)
                # If the addition of this entity will make the binary token grow too large,
                # send the buffer now.
                if self.binary_size + row_binary_len > module_vars.CONFIGS.max_token_size:
                    module_vars.QUERY_BUF.labels.append(self.to_binary())
                    module_vars.QUERY_BUF.send_buffer()
                    self.reset_partial_binary()
                    # Push the label onto the query buffer again, as there are more entities to process.
                    module_vars.QUERY_BUF.labels.append(self.to_binary())

                module_vars.QUERY_BUF.node_count += 1
                entities_created += 1
                self.binary_size += row_binary_len
                self.binary_entities.append(row_binary)
            module_vars.QUERY_BUF.labels.append(self.to_binary())
        self.infile.close()
        print("%d nodes created with label '%s'" % (entities_created, self.entity_str))
