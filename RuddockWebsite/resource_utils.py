class EnumValue():
  """
  EnumValue objects are meant to be used as elements of enums. They behave like
  integers, but can contain additional data as well since they are extendable
  objects. The equality and inequality operators are implemented, but other
  comparison operators are not because it does not make sense to do less
  than/greater than comparisons with enum values.
  """
  def __init__(self, value, **kwargs):
    """
    Sets value of the enum to the provided value. Can also set other attributes
    using kwargs.
    """
    self._value = value
    for key in kwargs:
      setattr(self, key, kwargs[key])
    return

  def __str__(self):
    return str(self._value)

  def __repr__(self):
    return repr(self._value)

  def __eq__(self, other):
    return self._value == other

  def __ne__(self, other):
    return not self.__eq__(other)

  def __trunc__(self):
    return self._value.__trunc__()
