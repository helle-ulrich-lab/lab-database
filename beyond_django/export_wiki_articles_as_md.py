from wiki.models.article import ArticleRevision

def save_wiki_article_as_md(article_id):
    from wiki.models.article import ArticleRevision
    from os.path import join
    from django_project.settings import BASE_DIR

    obj = ArticleRevision.objects.filter(article_id=article_id).latest('id')
    file_name = ''.join(obj.title.title().split()) + '.md'
    with open(join(BASE_DIR, 'db_backup/wiki_articles', file_name), 'w') as handle:
        handle.write(obj.content)

article_ids = set(ArticleRevision.objects.all().values_list('article_id', flat=True))
for article_id in article_ids:
    save_wiki_article_as_md(article_id)
