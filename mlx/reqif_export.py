from reqif_pyxb.ReqIF import *
import pyxb.binding.datatypes as datatypes

text_attribute = None

def reqif_document_setup():
    global text_attribute
    # Construct the header
    reqif_doc = REQ_IF(
        THE_HEADER=pyxb.BIND(),
        CORE_CONTENT=pyxb.BIND(),
        TOOL_EXTENSIONS=pyxb.BIND(),
    )
    reqif_doc.THE_HEADER.REQ_IF_HEADER=REQ_IF_HEADER(IDENTIFIER = "DOCUMENT_HEADER")

    content = REQ_IF_CONTENT()

    gen_id = ('x' + str(uuid.uuid1()))
    datatype_xhtml = DATATYPE_DEFINITION_XHTML(IDENTIFIER=gen_id, LAST_CHANGE=dateTime.today(), LONG_NAME="xhtml")
    content.add_datatype(datatype_xhtml)

    # The specification types
    text_attribute = ATTRIBUTE_DEFINITION_XHTML(LONG_NAME="Text", datatype=datatype_xhtml)
    requirement_object_type = SPEC_OBJECT_TYPE(LONG_NAME= "Requirement")
    requirement_object_type.add_attribute(text_attribute)

    test_object_type = SPEC_OBJECT_TYPE(LONG_NAME= "Test Case")
    test_object_type.add_attribute(text_attribute)

    spec_relation_type = SPEC_RELATION_TYPE(IDENTIFIER="_1link_type", LAST_CHANGE=dateTime.today(), LONG_NAME="selflink")
    specification_type = SPECIFICATION_TYPE(IDENTIFIER="_doc_type_ref", LAST_CHANGE=dateTime.today(), LONG_NAME="doc_type")

    # reqif_doc.CORE_CONTENT.REQ_IF_CONTENT.SPEC_TYPES = pyxb.BIND()
    content.add_spectype(spec_relation_type)
    content.add_spectype(requirement_object_type)
    content.add_spectype(test_object_type)
    content.add_spectype(specification_type)


    spec = SPECIFICATION(IDENTIFIER="SW_SPEC", spectype=specification_type, LONG_NAME="SW specification")
    content.add_specification(spec)

    reqif_doc.CORE_CONTENT.REQ_IF_CONTENT = content

    # print(reqif_doc.CORE_CONTENT.REQ_IF_CONTENT.SPEC_TYPES)
    reqif_doc.TOOL_EXTENSIONS.REQ_IF_TOOL_EXTENSION.append(REQ_IF_TOOL_EXTENSION())
    return reqif_doc


def add_requirement(reqif_doc):
    content = reqif_doc.CORE_CONTENT.REQ_IF_CONTENT

    specification = content.SPECIFICATIONS


    requirement_object_type = content.SPEC_TYPES.SPEC_OBJECT_TYPE[1]
    # The actual requirements
    requirement_1 = SPEC_OBJECT(IDENTIFIER="SWRQT-ANGLE_CALCUL", spectype=requirement_object_type)
    requirement_1.VALUES.append(ATTRIBUTE_VALUE_XHTML(definition=text_attribute, value="Hallo"))
    content.add_specobject(requirement_1)
    specification.SPECIFICATION[0].add_spec_hierarchy(SPEC_HIERARCHY(IDENTIFIER="RANDOM_ID1", spec_object=requirement_1))

    requirement_2 = SPEC_OBJECT(IDENTIFIER="SWRQT-FIELD_CALCUL", spectype=requirement_object_type)
    requirement_2.VALUES.append(ATTRIBUTE_VALUE_XHTML(definition=text_attribute, value="Hallo3"))
    content.add_specobject(requirement_2)
    specification.SPECIFICATION[0].add_spec_hierarchy(SPEC_HIERARCHY(IDENTIFIER="RANDOM_ID2", spec_object=requirement_2))

    spec_relation_type = content.SPEC_TYPES.SPEC_RELATION_TYPE[0]
    # Relationships between requirements
    content.add_spec_relation(
        SPEC_RELATION(
            IDENTIFIER="_self_link",
            source_spec_object=requirement_1,
            target_spec_object=requirement_2,
            link_type=spec_relation_type))

def export_xml(reqif_doc, outfile):
    print(outfile)
    with open(outfile, 'w') as out:
        try:
            xml_content = reqif_doc.toxml()
            print(xml_content, file=out)
        except Exception as e:
            print(e.details())
