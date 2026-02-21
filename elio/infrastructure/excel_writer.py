import pandas as pd


class ExcelWriter:

    @staticmethod
    def write(nodes, path):
        rows = []

        for node in nodes:
            for module in node.modules:
                for signal in module.signals:
                    rows.append({
                        "Node": node.node_id,
                        "Slot": module.slot_number,
                        "Module": module.template_name,
                        "Signal": signal.tag
                    })

        df = pd.DataFrame(rows)
        df.to_excel(path, index=False)