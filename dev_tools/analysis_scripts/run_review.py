import importlib.util, pathlib, traceback
p = pathlib.Path(r"C:\Working\Others\Python\Cloud App Projects\Design Input Review.py")
spec = importlib.util.spec_from_file_location("design_input_review", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Review = mod.DesignInputReview
r = Review()
try:
    ok = r.run_complete_review()
    print('run_complete_review returned', ok)
except Exception:
    traceback.print_exc()
