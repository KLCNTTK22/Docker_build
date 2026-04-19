class ASTNode:

    def __init__(self, type_, tag=None, text=None):

        self.type = type_
        self.tag = tag
        self.text = text

        # formatting
        self.properties = {}

        # layout information
        self.layout = {}

        # style reference
        self.style = {}

        # list / numbering
        self.list = {}

        # section information
        self.section = {}

        # XML attributes
        self.attributes = {}

        # references (hyperlink, image, footnote...)
        self.references = []

        # child nodes
        self.children = []

        # unsupported tags
        self.unknown = []

        # parsing errors
        self.errors = []

    def add_child(self, node):
        if node:
            self.children.append(node)

    def add_reference(self, ref):
        self.references.append(ref)

    def add_error(self, error):
        self.errors.append(str(error))

    def add_unknown(self, tag):
        self.unknown.append(tag)

    def to_dict(self):

        return {
            "type": self.type,
            "tag": self.tag,
            "text": self.text,
            "properties": self.properties,
            "layout": self.layout,
            "style": self.style,
            "list": self.list,
            "section": self.section,
            "attributes": self.attributes,
            "references": self.references,
            "children": [c.to_dict() for c in self.children],
            "unknown": self.unknown,
            "errors": self.errors,
        }