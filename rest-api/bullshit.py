
def stupid_test() -> None:
    squares = [i*i for i in range(4)]

    def stupid_function(x=None):
        if x is None:
            return "".join(str(i) for i in squares)
        return x
    _ = stupid_function()
    return _

def no(x=0):
    try:
        return [None][x]
    except Exception:
        return None
