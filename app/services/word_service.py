import aiohttp
import random

async def get_word_definitions(length=None, number=1):
    results = []
    attempts = 0
    max_attempts = 5
    
    async with aiohttp.ClientSession() as session:
        while len(results) < number and attempts < max_attempts:
            attempts += 1
            needed = number - len(results)
            fetch_count = needed * 2 
            
            url = f"https://random-word-api.herokuapp.com/word?number={fetch_count}"
            if length and length > 0:
                url += f"&length={length}"
            
            async with session.get(url) as rw_response:
                if rw_response.status != 200:
                    break
                words = await rw_response.json()

            for word in words:
                if len(results) >= number:
                    break
                
                dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                async with session.get(dict_url) as d_response:
                    if d_response.status == 200:
                        data = await d_response.json()
                        try:
                            definition = data[0]['meanings'][0]['definitions'][0]['definition']
                            results.append({
                                "word": word,
                                "definition": definition,
                                "length": len(word)
                            })
                        except (IndexError, KeyError):
                            continue
                    else:
                        continue
        
    return results

async def get_quiz_data(length=0):
    url = f"https://random-word-api.herokuapp.com/word?number=10"
    if length > 0:
        url += f"&length={length}"
        
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            words = await response.json()
            
        correct_word = None
        definition = None
        
        for word in words:
            dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with session.get(dict_url) as d_response:
                if d_response.status == 200:
                    data = await d_response.json()
                    try:
                        definition = data[0]['meanings'][0]['definitions'][0]['definition']
                        correct_word = word
                        break
                    except (IndexError, KeyError):
                        continue
        
        if not correct_word:
            return None
            
        distractors = [w for w in words if w != correct_word][:3]
        if len(distractors) < 3:
            distractors += ["apple", "ocean", "cloud"]
            distractors = distractors[:3]
            
        options = distractors + [correct_word]
        random.shuffle(options)
        
        return {
            "question": f"❓ *Guess the word by its definition:*\n\n📖 \"{definition}\"",
            "correct": correct_word,
            "options": options
        }
