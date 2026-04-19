class FeatureReport:

    def __init__(self):

        self.features = {}
        self.unknown_tags = set()
        self.errors = []

    def add_feature(self, name):

        self.features[name] = self.features.get(name,0)+1

    def add_unknown(self, tag):

        self.unknown_tags.add(tag)

    def add_error(self, error):

        self.errors.append(error)

    def summary(self):

        return {
            "features": self.features,
            "unknown_tags": list(self.unknown_tags),
            "errors": self.errors
        }