from ..world import World, Header, Location

class WorldGenerator:
    def generate_world() -> World:
        header: Header = Header("Test world", "location0")
        location: Location = Location(
            name="void", 
            description="An empty black void. There is nothing here. How you can even breathe is a mystery.",
            exits={})
        return World(
            header, 
            flags=[], 
            items={}, 
            locations={}, 
            npcs={}, 
            interactions=[])
        
