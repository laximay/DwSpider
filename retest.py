import re

str = '<table class="mb_l_mb_r_tb"><tr><td>safdsf</td><td>fsdfd</td></tr></table>'
p = re.compile(r'<table class="mb_l_mb_r_tb.*?>(.*?)</table>')

res = re.search(p, str);
if res:
    print(res.group())
else:
    print('匹配失败！')

