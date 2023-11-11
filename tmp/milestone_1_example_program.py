# DYNAPYT: DO NOT INSTRUMENT


import dynapyt.runtime as _rt

_dynapyt_ast_ = "/Users/felixneubauer/Documents/Business/Uni_Stuttgart/Semester 4/ProgramAnalysis/project/dynamicslicing/tmp/milestone_1_example_program.py" + ".orig"
try:
    def slice_me():
        x = _rt._write_(_dynapyt_ast_, 1, 5, [lambda: x])
        print("Hello World")
        if x < 10:
            x += _rt._aug_assign_(_dynapyt_ast_, 2, lambda: x, 0, 5)
        y = _rt._write_(_dynapyt_ast_, 3, 0, [lambda: y])
        return y
    
    
    slice_me()
except Exception as _dynapyt_exception_:
    _rt._catch_(_dynapyt_exception_)

