from reqif_pyxb.ReqIF import *
import pyxb.binding.datatypes as datatypes
import hashlib

requirement_object_type = None

def reqif_document_setup():
    global requirement_object_type
    # Construct the header
    reqif_doc = REQ_IF(
        THE_HEADER=pyxb.BIND(),
        CORE_CONTENT=pyxb.BIND(),
        TOOL_EXTENSIONS=pyxb.BIND(),
    )
    reqif_doc.THE_HEADER.REQ_IF_HEADER=REQ_IF_HEADER()

    content = REQ_IF_CONTENT()

    datatype_string = DATATYPE_DEFINITION_STRING(LONG_NAME="string")
    datatype_int = DATATYPE_DEFINITION_INTEGER(LONG_NAME="integer", MIN=0, MAX=65535)
    content.add_datatype(datatype_string)

    # The specification types
    text_attribute = ATTRIBUTE_DEFINITION_STRING(LONG_NAME="Text", datatype=datatype_string)
    caption_attribute = ATTRIBUTE_DEFINITION_STRING(LONG_NAME="Caption", datatype=datatype_string)
    content_hash_attribute = ATTRIBUTE_DEFINITION_STRING(LONG_NAME="Content hash", datatype=datatype_string)
    document_name_attribute = ATTRIBUTE_DEFINITION_STRING(LONG_NAME="Document", datatype=datatype_string)
    line_number_attribute = ATTRIBUTE_DEFINITION_INTEGER(LONG_NAME="Line number", datatype=datatype_int)
    requirement_object_type = SPEC_OBJECT_TYPE(LONG_NAME= "Requirement")
    requirement_object_type.add_attribute(text_attribute)
    requirement_object_type.add_attribute(caption_attribute)
    requirement_object_type.add_attribute(content_hash_attribute)
    requirement_object_type.add_attribute(document_name_attribute)
    requirement_object_type.add_attribute(line_number_attribute)

    specification_type = SPECIFICATION_TYPE(LONG_NAME="doc_type")

    # reqif_doc.CORE_CONTENT.REQ_IF_CONTENT.SPEC_TYPES = pyxb.BIND()

    content.add_spectype(requirement_object_type)
    content.add_spectype(specification_type)


    spec = SPECIFICATION(spectype=specification_type, LONG_NAME="SW specification")
    content.add_specification(spec)

    reqif_doc.CORE_CONTENT.REQ_IF_CONTENT = content

    # print(reqif_doc.CORE_CONTENT.REQ_IF_CONTENT.SPEC_TYPES)
    reqif_doc.TOOL_EXTENSIONS.REQ_IF_TOOL_EXTENSION.append(REQ_IF_TOOL_EXTENSION())
    return reqif_doc


def add_relation(reqif_doc, relation):
    content = reqif_doc.CORE_CONTENT.REQ_IF_CONTENT
    content.add_spectype(SPEC_RELATION_TYPE(LONG_NAME=relation))
    print(relation)

def add_requirement(reqif_doc, item):
    content = reqif_doc.CORE_CONTENT.REQ_IF_CONTENT
    specification = content.SPECIFICATIONS

    if item.content:
        content_hash = hashlib.md5(item.content.encode('utf-8')).hexdigest()
    else:
        content_hash = "0"

    # The actual requirements
    requirement = SPEC_OBJECT(IDENTIFIER=item.id, LONG_NAME=item.get_name(), spectype=requirement_object_type)
    requirement.set_value("Text", item.content if item.content else '-')
    requirement.set_value("Caption", item.caption if item.caption else '-')
    requirement.set_value("Content hash", content_hash)
    requirement.set_value("Line number", item.lineno if item.lineno else 0)
    requirement.set_value("Document", item.docname if item.docname else '-')
    content.add_specobject(requirement)
    specification.SPECIFICATION[0].add_spec_hierarchy(SPEC_HIERARCHY(spec_object=requirement))

    for relation in item.iter_relations():
        tgts = item.iter_targets(relation)
        for target in tgts:
            content.add_spec_relation_by_ID(item.id, target, relation)

def export_xml(reqif_doc, outfile):
    print(outfile)
    with open(outfile, 'w') as out:
        try:
            xml_content = reqif_doc.toxml()
            print(xml_content, file=out)
        except Exception as e:
            print(e.details())
