import pytest
from game.YamlUtil import YamlUtil
from game.GameError import GameError


# simplify_name

def test_simplify_name_valid():
    assert YamlUtil.simplify_name('sword') == 'sword'

def test_simplify_name_normalizes_case_and_space():
    assert YamlUtil.simplify_name('  Iron   Sword ') == 'iron sword'

def test_simplify_name_invalid_characters():
    assert YamlUtil.simplify_name('sword!') == ''

def test_simplify_name_non_string():
    assert YamlUtil.simplify_name(123) == ''
    assert YamlUtil.simplify_name(None) == ''


# get_names

def test_get_names_unique():
    result = YamlUtil.get_names([{'name': 'sword'}, {'name': 'shield'}])
    assert sorted(result) == ['shield', 'sword']

def test_get_names_simplifies():
    result = YamlUtil.get_names([{'name': 'Iron Sword'}])
    assert result == ['iron sword']

def test_get_names_duplicate_raises():
    with pytest.raises(GameError):
        YamlUtil.get_names([{'name': 'sword'}, {'name': 'Sword'}])

def test_get_names_invalid_raises():
    with pytest.raises(GameError):
        YamlUtil.get_names([{'name': 'bad name!'}])

def test_get_names_missing_name_raises():
    with pytest.raises(GameError):
        YamlUtil.get_names([{'description': 'no name here'}])


# parse_minmax_object

def test_parse_minmax_separate_keys():
    result = YamlUtil.parse_minmax_object({'min_hp': '1', 'max_hp': '3'}, 'hp', int)
    assert result == {'min': 1, 'max': 3}

def test_parse_minmax_single_key():
    result = YamlUtil.parse_minmax_object({'hp': 5}, 'hp', int)
    assert result == {'min': 5, 'max': 5}

def test_parse_minmax_default():
    result = YamlUtil.parse_minmax_object({}, 'hp', int, default=0)
    assert result == {'min': 0, 'max': 0}

def test_parse_minmax_missing_required_raises():
    with pytest.raises(GameError):
        YamlUtil.parse_minmax_object({}, 'hp', int)

def test_parse_minmax_transform_failure_raises_gameerror():
    with pytest.raises(GameError):
        YamlUtil.parse_minmax_object({'hp': 'not_a_number'}, 'hp', int)


# get_yaml_filename

def test_get_yaml_filename_yml(tmp_path):
    (tmp_path / 'enemies.yml').write_text('name: a\n')
    result = YamlUtil.get_yaml_filename(str(tmp_path), 'enemies')
    assert result.endswith('enemies.yml')

def test_get_yaml_filename_yaml(tmp_path):
    (tmp_path / 'enemies.yaml').write_text('name: a\n')
    result = YamlUtil.get_yaml_filename(str(tmp_path), 'enemies')
    assert result.endswith('enemies.yaml')

def test_get_yaml_filename_missing_raises(tmp_path):
    with pytest.raises(GameError):
        YamlUtil.get_yaml_filename(str(tmp_path), 'enemies')


# get_yaml_object

def test_get_yaml_object_valid(tmp_path):
    f = tmp_path / 'obj.yaml'
    f.write_text('name: sword\nuses: 3\n')
    assert YamlUtil.get_yaml_object(str(f)) == {'name': 'sword', 'uses': 3}

def test_get_yaml_object_missing_file_raises(tmp_path):
    with pytest.raises(GameError):
        YamlUtil.get_yaml_object(str(tmp_path / 'missing.yaml'))

def test_get_yaml_object_empty_file_raises(tmp_path):
    f = tmp_path / 'empty.yaml'
    f.write_text('')
    with pytest.raises(GameError):
        YamlUtil.get_yaml_object(str(f))

def test_get_yaml_object_invalid_yaml_raises(tmp_path):
    f = tmp_path / 'bad.yaml'
    f.write_text(':\n  - [unclosed\n')
    with pytest.raises(GameError):
        YamlUtil.get_yaml_object(str(f))

def test_get_yaml_object_non_mapping_raises(tmp_path):
    f = tmp_path / 'list.yaml'
    f.write_text('- 1\n- 2\n')
    with pytest.raises(GameError):
        YamlUtil.get_yaml_object(str(f))


# load_yaml_data

def test_load_yaml_data_single_file(tmp_path):
    f = tmp_path / 'main.yaml'
    f.write_text('name: main\n')
    result = YamlUtil.load_yaml_data(str(f))
    assert result == [{'name': 'main'}]

def test_load_yaml_data_include_relative_to_including_file(tmp_path):
    sub = tmp_path / 'sub'
    sub.mkdir()
    (tmp_path / 'main.yaml').write_text('name: main\ninclude:\n  - sub/more.yaml\n')
    (sub / 'more.yaml').write_text('name: more\n')
    result = YamlUtil.load_yaml_data(str(tmp_path / 'main.yaml'))
    names = sorted(obj['name'] for obj in result)
    assert names == ['main', 'more']

def test_load_yaml_data_removes_include_key(tmp_path):
    (tmp_path / 'main.yaml').write_text('name: main\ninclude:\n  - other.yaml\n')
    (tmp_path / 'other.yaml').write_text('name: other\n')
    result = YamlUtil.load_yaml_data(str(tmp_path / 'main.yaml'))
    assert all('include' not in obj for obj in result)

def test_load_yaml_data_circular_include(tmp_path):
    (tmp_path / 'a.yaml').write_text('name: a\ninclude:\n  - b.yaml\n')
    (tmp_path / 'b.yaml').write_text('name: b\ninclude:\n  - a.yaml\n')
    result = YamlUtil.load_yaml_data(str(tmp_path / 'a.yaml'))
    names = sorted(obj['name'] for obj in result)
    assert names == ['a', 'b']

def test_load_yaml_data_self_include(tmp_path):
    (tmp_path / 'self.yaml').write_text('name: self\ninclude:\n  - self.yaml\n')
    result = YamlUtil.load_yaml_data(str(tmp_path / 'self.yaml'))
    assert result == [{'name': 'self'}]

def test_load_yaml_data_missing_include_raises(tmp_path):
    (tmp_path / 'main.yaml').write_text('name: main\ninclude:\n  - missing.yaml\n')
    with pytest.raises(GameError):
        YamlUtil.load_yaml_data(str(tmp_path / 'main.yaml'))

def test_load_yaml_data_include_not_a_list_raises(tmp_path):
    (tmp_path / 'main.yaml').write_text('name: main\ninclude: 5\n')
    with pytest.raises(GameError):
        YamlUtil.load_yaml_data(str(tmp_path / 'main.yaml'))
