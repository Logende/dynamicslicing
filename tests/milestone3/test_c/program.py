def slice_me():
    a = 0
    if a == 4:
        a = 7
    if a > 3:
        a += 5
    else:
        a = 3
    i = 0
    while i < 5:
        a += 3
        i += 1
    return a # slicing criterion
slice_me()