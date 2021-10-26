import os
import requests

from argparse import ArgumentParser
from lxml import etree
from unicodedata import normalize



def get_args():
    parser = ArgumentParser(description='Process some HelloFresh recipes')
    parser.add_argument('urls', nargs='+', help='the urls of the recipe on HelloFresh')

    return parser.parse_args()


def fix_text(text, replace_spaces=True, lower=True):
    replacements = [
        ('&', 'and'),
        ('\n', ' '),
        ('\u2044', '/'),
        ('ounces', 'oz'),
        ('ounce', 'oz'),
        ('teaspoons', 'tsp'),
        ('teaspoon', 'tsp'),
        ('tablespoons', 'tbsp'),
        ('tablespoon', 'tbsp'),
    ]

    if not text:
        return

    text = text.strip()
    if not text:
        return

    if lower:
        text = text.lower()

    text = normalize('NFKC', text)

    for from_val, to_val in replacements:
        text = text.replace(from_val, to_val)

    if replace_spaces:
        text = text.replace(' ', '_')

    return text

def get_page_root(url):
    try:
        html = requests.get(url)
        if not html.ok:
            print('Could not get html: {} {}'.format(html.status_code, html.reason))
            return

        return etree.fromstring(html.text, parser=etree.HTMLParser(recover=True))
    except Exception as e:
        print('Could not get page root: {}'.format(e))
        return


def get_filename(root):
    title_attr = root.xpath('//h1[@data-test-id=\'recipeDetailFragment.recipe-name\']')
    if not title_attr:
        raise Exception('Could not find title')

    title_attr = title_attr[0]
    title = title_attr.text
    subtitle = title_attr.getparent().xpath('h4')

    if subtitle:
        title += ' ' + subtitle[0].text
    else:
        print('Warning: could not find subtitle')

    filename = os.path.join('recipes', 'meals', fix_text(title) + '.txt')

    if os.path.exists(filename):
        raise Exception('File already exists: {}'.format(filename))

    return filename


def get_ingredients(root):
    ingredients_attrs = root.xpath('//div[@class=\'fela-_1qz307e\']')
    if not ingredients_attrs:
        raise Exception('Could not find ingredients')

    ingredients = []
    for ingredients_attr in ingredients_attrs:
        ingredient_values = []

        for ingredient in ingredients_attr.xpath('p'):
            if not ingredient.text:
                continue

            ingredient_values.append('- {}'.format(ingredient.text))

        ingredients.append(fix_text(' '.join(ingredient_values), replace_spaces=False))

    return '\n'.join(ingredients)


def get_instructions(root):
    instructions_attrs = []
    for instructions_attr in root.xpath('//div[starts-with(@data-test-id, recipeDetailFragment)]'):
        if instructions_attr.attrib.get('data-test-id', '').startswith('recipeDetailFragment.instructions.step-'):
            instructions_attrs.append(instructions_attr)

    if not instructions_attrs:
        raise Exception('Could not find instructions')

    instructions = []
    for instructions_attr in instructions_attrs:
        title_attr = instructions_attr.xpath('.//img')
        if title_attr:
            title = title_attr[0].attrib.get('alt', '')
        else:
            title = ''

        instruction_list = []
        count = 1
        for instruction in instructions_attr.xpath('.//p'):
            for value in instruction.text.split('\u2022'):
                value = fix_text(value, replace_spaces=False, lower=False)
                if not value:
                    continue

                instruction_list.append('{}. {}'.format(count, value))
                count += 1

        if not instruction_list:
            continue

        if title:
            instructions.append('#### {}'.format(title))

        instructions.extend(instruction_list)
        instructions.append('')

    instructions = instructions[:-1]
    return '\n'.join(instructions)


def write_file(filename, ingredients, instructions):
    with open(filename, 'w') as f:
        f.write('### Ingredients:\n{}\n\n### Instructions:\n{}\n'.format(ingredients, instructions))

    print('Wrote: {}'.format(filename))

def main():
    args = get_args()
    for url in args.urls:
        root = get_page_root(url)
        if root is None:
            continue

        ingredients = get_ingredients(root)
        try:
            filename = get_filename(root)
            ingredients = get_ingredients(root)
            instructions = get_instructions(root)

            write_file(filename, ingredients, instructions)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    main()
