"""One-off restore migration: lesson video URLs that were accidentally blanked.

Moved out of server.py so startup lives lean and the URL catalog is reviewable
as data. The migration itself is idempotent — guarded by a system-collection
flag (`video_restore_v1`) the first run inserts.
"""

VIDEO_URLS = {
    'welcome-why-ai-matters-for-women': 'https://www.youtube.com/embed/2ePf9rue1Ao',
    'what-is-ai-in-simple-terms': 'https://www.youtube.com/embed/ad79nYk2keg',
    'machine-learning-vs-deep-learning': 'https://www.youtube.com/embed/zjkBMFhNj_g',
    'how-chatgpt-actually-works': 'https://www.youtube.com/embed/w65p_IIp6JY',
    'your-first-ai-powered-task': 'https://www.youtube.com/embed/Yq0QkCxoTHM',
    'anatomy-of-a-great-prompt': 'https://www.youtube.com/embed/jC4v5AS4RIM',
    'role-context-task-framework': 'https://www.youtube.com/embed/dOxUroR57xs',
    'chain-of-thought-prompting': 'https://www.youtube.com/embed/H4olM_mExl8',
    'writing-content-that-converts': 'https://www.youtube.com/embed/aircAruvnKk',
    'building-a-research-assistant': 'https://www.youtube.com/embed/IHZwWFHWa-w',
    'custom-gpts-and-personas': 'https://www.youtube.com/embed/J0Aq44Pze-w',
    'ai-income-landscape-2026': 'https://www.youtube.com/embed/m_d3kI23wlw',
    'niche-selection-your-unfair-advantage': 'https://www.youtube.com/embed/H9M3n90gqdQ',
    'ai-content-creation-as-a-service': 'https://www.youtube.com/embed/JTxsNm9IdYU',
    'designing-digital-products-with-ai': 'https://www.youtube.com/embed/8jLOx1hD3_o',
    'ai-virtual-assistant-business': 'https://www.youtube.com/embed/iAyJG-pYS9I',
    'marketing-yourself-online': 'https://www.youtube.com/embed/1aA1WGON49E',
    'pricing-payments-and-scaling': 'https://www.youtube.com/embed/u3rqe6jbAQc',
    'ai-career-paths-for-women-2026': 'https://www.youtube.com/embed/3yPBVii7Ct0',
    'deep-dive-prompt-engineering': 'https://www.youtube.com/embed/p09yRj47kNM',
    'ai-tools-every-pro-must-know': 'https://www.youtube.com/embed/eyTtAheVm9w',
    'building-an-ai-portfolio': 'https://www.youtube.com/embed/dPq7DDjBfnE',
    'networking-personal-branding': 'https://www.youtube.com/embed/wOdmiOAYjQ4',
    'consultancy-charge-50k-per-project': 'https://www.youtube.com/embed/JBoT_pEwiP0',
    'interview-prep-for-ai-roles': 'https://www.youtube.com/embed/o42Cb1pTNVk',
    'your-90-day-action-plan': 'https://www.youtube.com/embed/qXcUkN2x8KM',
}


async def restore_blank_lesson_videos(db):
    """Run once: restore video_url on lessons whose title matches a known slug
    and whose url was blanked. Returns the number of lessons updated."""
    flag = await db.system.find_one({'_id': 'video_restore_v1'})
    if flag:
        return 0

    restored = 0
    for slug, url in VIDEO_URLS.items():
        title_pattern = slug.replace('-', ' ').split()[0]
        res = await db.lessons.update_many(
            {'title': {'$regex': title_pattern, '$options': 'i'}, 'video_url': ''},
            {'$set': {'video_url': url}}
        )
        restored += res.modified_count

    await db.system.insert_one({'_id': 'video_restore_v1', 'restored_lessons': restored})
    return restored
