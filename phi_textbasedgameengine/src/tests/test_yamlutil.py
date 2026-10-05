import pytest
from game.YamlUtil import YamlUtil
from game.GameError import GameError


def write(path, content):
	path.write_text(content)
	return str(path)


def test_load_single_file(tmp_path):
	fname = write(tmp_path / 'obj.yml', 'name: thing\nvalue: 3\n')

	objects = YamlUtil.load_yaml_data(fname)

	assert objects == [{'name': 'thing', 'value': 3}]

def test_load_includes(tmp_path):
	write(tmp_path / 'b.yml', 'name: b\n')
	fname = write(tmp_path / 'a.yml', 'name: a\ninclude:\n  - b.yml\n')

	objects = YamlUtil.load_yaml_data(fname)

	names = [obj['name'] for obj in objects]
	assert sorted(names) == ['a', 'b']
	assert all('include' not in obj for obj in objects)

def test_include_paths_are_relative_to_including_file(tmp_path):
	subdir = tmp_path / 'sub'
	subdir.mkdir()
	write(subdir / 'b.yml', 'name: b\n')
	fname = write(subdir / 'a.yml', 'name: a\ninclude:\n  - b.yml\n')

	objects = YamlUtil.load_yaml_data(fname)

	assert sorted(obj['name'] for obj in objects) == ['a', 'b']

def test_duplicate_include_loaded_once(tmp_path):
	write(tmp_path / 'c.yml', 'name: c\n')
	write(tmp_path / 'b.yml', 'name: b\ninclude:\n  - c.yml\n')
	fname = write(tmp_path / 'a.yml', 'name: a\ninclude:\n  - b.yml\n  - c.yml\n')

	objects = YamlUtil.load_yaml_data(fname)

	assert sorted(obj['name'] for obj in objects) == ['a', 'b', 'c']

def test_circular_include_raises(tmp_path):
	write(tmp_path / 'b.yml', 'name: b\ninclude:\n  - a.yml\n')
	fname = write(tmp_path / 'a.yml', 'name: a\ninclude:\n  - b.yml\n')

	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(fname)

	assert 'Circular include' in str(errinfo.value)

def test_self_include_raises(tmp_path):
	fname = write(tmp_path / 'a.yml', 'name: a\ninclude:\n  - a.yml\n')

	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(fname)

	assert 'Circular include' in str(errinfo.value)

def test_missing_file_raises(tmp_path):
	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(str(tmp_path / 'nope.yml'))

	assert 'Could not find yaml file' in str(errinfo.value)

def test_missing_include_raises(tmp_path):
	fname = write(tmp_path / 'a.yml', 'name: a\ninclude:\n  - nope.yml\n')

	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(fname)

	assert 'Could not find yaml file' in str(errinfo.value)

def test_empty_file_loads_as_empty_object(tmp_path):
	fname = write(tmp_path / 'a.yml', '')

	objects = YamlUtil.load_yaml_data(fname)

	assert objects == [{}]

def test_invalid_yaml_raises(tmp_path):
	fname = write(tmp_path / 'a.yml', 'name: [unclosed\n')

	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(fname)

	assert 'Error parsing yaml file' in str(errinfo.value)

def test_non_object_yaml_raises(tmp_path):
	fname = write(tmp_path / 'a.yml', '- just\n- a\n- list\n')

	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(fname)

	assert 'Expected a yaml object' in str(errinfo.value)

def test_include_not_a_list_raises(tmp_path):
	fname = write(tmp_path / 'a.yml', 'name: a\ninclude: b.yml\n')

	with pytest.raises(GameError) as errinfo:
		YamlUtil.load_yaml_data(fname)

	assert "'include'" in str(errinfo.value)

def test_get_yaml_filename(tmp_path):
	write(tmp_path / 'obj.yml', 'name: x\n')
	write(tmp_path / 'other.yaml', 'name: y\n')

	assert YamlUtil.get_yaml_filename(str(tmp_path), 'obj').endswith('obj.yml')
	assert YamlUtil.get_yaml_filename(str(tmp_path), 'other').endswith('other.yaml')
	with pytest.raises(GameError):
		YamlUtil.get_yaml_filename(str(tmp_path), 'missing')

def test_parse_minmax_object(tmp_path):
	assert YamlUtil.parse_minmax_object({'min_x': 1, 'max_x': 5}, 'x', int) == {'min': 1, 'max': 5}
	assert YamlUtil.parse_minmax_object({'x': '3'}, 'x', int) == {'min': 3, 'max': 3}
	assert YamlUtil.parse_minmax_object({}, 'x', int, default=7) == {'min': 7, 'max': 7}

def test_parse_minmax_object_missing_required():
	with pytest.raises(GameError) as errinfo:
		YamlUtil.parse_minmax_object({}, 'x', int)

	assert "'x' is a required field" in str(errinfo.value)

def test_parse_minmax_object_bad_transform():
	with pytest.raises(GameError) as errinfo:
		YamlUtil.parse_minmax_object({'x': 'abc'}, 'x', int)

	assert "Error formatting property 'x'" in str(errinfo.value)

def test_get_names_simplifies_and_uniques():
	objects = [{'name': 'Goblin  King'}, {'name': 'slime'}]

	names = YamlUtil.get_names(objects)

	assert sorted(names) == ['goblin king', 'slime']

def test_get_names_duplicate_raises():
	objects = [{'name': 'Goblin'}, {'name': 'goblin'}]

	with pytest.raises(GameError) as errinfo:
		YamlUtil.get_names(objects)

	assert 'used multiple times' in str(errinfo.value)

def test_get_names_invalid_raises():
	with pytest.raises(GameError) as errinfo:
		YamlUtil.get_names([{'name': '!!!'}])

	assert 'is invalid' in str(errinfo.value)

def test_simplify_name():
	assert YamlUtil.simplify_name('  Goblin   King ') == 'goblin king'
	assert YamlUtil.simplify_name('sword_2') == 'sword_2'
	assert YamlUtil.simplify_name('bad!name') == ''
	assert YamlUtil.simplify_name('2starts_with_digit') == ''
