class Person:
    def __init__(self, age):
        self.age = age
def slice_me():
    p1 = Person(1)
    p2 = p1
    p2.age += 5
    text = "p1 age is " + str(p1.age)
    unused_list = [1, 2, 3]
    unused_list.append(text)
    result = ["text1"]
    result.append("text2")
    result.append(text)
    return result # slicing criterion
slice_me()