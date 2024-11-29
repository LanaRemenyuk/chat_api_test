import phonenumbers


class PhoneNumber(str):
    """Кастомный класс для валидации номера телефона"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, *args, **kwargs):
        if not isinstance(value, str):
            raise TypeError('Введенный номер не является строкой')
        try:
            phone = phonenumbers.parse(value)
            if not phonenumbers.is_valid_number(phone):
                raise ValueError('Некорректный номер')
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValueError('Некорректный формат номера')
        return value