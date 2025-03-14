# helper class to print a table of values to a console (or text file)


class TableColumn:
    def __init__(self, objName, text, length):
        self.objName = objName
        self.text = text
        self.length = length

    def get_objName(self):
        return self.objName

    def get_text(self):
        return self.text

    def get_length(self):
        return self.length


class TableHelper:
    def __init__(self):
        self.columns = []

    def add_column(self, col):
        self.columns.append(col)

    # returns the header
    def gen_header(self):
        ret = ""
        for col in self.columns:
            value = col.get_text()
            ret += value
            ret += " " * (col.get_length() - len(value))
            ret += " "
        return ret

    def gen_line_divider(self):
        ret = ""
        for col in self.columns:
            value = col.get_text()
            ret += "-" * col.get_length()
            ret += " "
        return ret

    def gen_line_from_object(self, obj):
        ret = ""
        for col in self.columns:
            # lookup value
            try:
                value = str(obj[col.get_objName()])
            except Exception:
                value = ""

            ret += value
            ret += " " * (col.get_length() - len(value))
            ret += " "
        return ret
