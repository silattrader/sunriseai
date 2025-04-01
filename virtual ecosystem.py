import random
import time
import os
import copy # Used for safely iterating while modifying lists

# --- Configuration ---
GRID_WIDTH = 30
GRID_HEIGHT = 15
INITIAL_PLANTS = 50
INITIAL_HERBIVORES = 15
INITIAL_CARNIVORES = 5
NUM_STEPS = 150 # Total simulation time steps

# Plant properties
PLANT_REGEN_RATE = 0.1 # Chance per empty cell to grow a plant each step
PLANT_ENERGY = 5

# Herbivore properties
HERBIVORE_MAX_ENERGY = 50
HERBIVORE_MOVE_COST = 1
HERBIVORE_REPRODUCE_THRESHOLD = 40
HERBIVORE_REPRODUCE_COST = 20
HERBIVORE_EAT_GAIN = PLANT_ENERGY * 2 # Energy gained from eating a plant
HERBIVORE_MAX_AGE = 40
HERBIVORE_SIGHT_RANGE = 3

# Carnivore properties
CARNIVORE_MAX_ENERGY = 100
CARNIVORE_MOVE_COST = 2 # More costly to move
CARNIVORE_REPRODUCE_THRESHOLD = 80
CARNIVORE_REPRODUCE_COST = 40
CARNIVORE_EAT_GAIN = 30 # Energy gained from eating a herbivore
CARNIVORE_MAX_AGE = 50
CARNIVORE_SIGHT_RANGE = 5

# Display settings
CLEAR_SCREEN = True # Set to False if running in an environment where os.system('cls') or 'clear' doesn't work well
FRAME_DELAY = 0.2 # Seconds between simulation steps

# --- Classes ---

class Organism:
    """Base class for all living things in the ecosystem."""
    def __init__(self, x, y, max_energy, move_cost, reproduce_threshold, reproduce_cost, max_age, sight_range):
        self.x = x
        self.y = y
        self.max_energy = max_energy
        self.energy = max_energy // 2 # Start with half energy
        self.move_cost = move_cost
        self.reproduce_threshold = reproduce_threshold
        self.reproduce_cost = reproduce_cost
        self.max_age = max_age
        self.age = 0
        self.sight_range = sight_range

    def _is_valid_pos(self, x, y, width, height):
        return 0 <= x < width and 0 <= y < height

    def move(self, environment):
        if self.energy <= self.move_cost:
            return # Not enough energy to move

        # Simple random walk
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])

        new_x, new_y = self.x + dx, self.y + dy

        # Check boundaries and if the target cell is empty (for simplicity)
        if self._is_valid_pos(new_x, new_y, environment.width, environment.height) and \
           environment.get_organism_at(new_x, new_y) is None:
             # Only move if target is empty to avoid simple collision issues
             # More complex logic could handle interactions/displacements
            self.x = new_x
            self.y = new_y
            self.energy -= self.move_cost

    def age_and_check_death(self):
        self.age += 1
        self.energy -= 1 # Basic metabolic cost
        if self.energy <= 0 or self.age > self.max_age:
            return True # Signal death
        return False

    def try_reproduce(self, environment):
        if self.energy >= self.reproduce_threshold:
            self.energy -= self.reproduce_cost
            # Find an empty adjacent spot for offspring
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = self.x + dx, self.y + dy
                    if self._is_valid_pos(nx, ny, environment.width, environment.height) and \
                       environment.get_organism_at(nx, ny) is None and \
                       environment.get_plant_at(nx, ny) is None:
                        # Create offspring of the same type
                        offspring = type(self)(nx, ny) # Creates Herbivore if self is Herbivore, etc.
                        offspring.energy = self.reproduce_cost // 2 # Give offspring some starting energy
                        return offspring # Return the new offspring object
        return None # No reproduction occurred

    def update(self, environment):
        # Default update: age, check death. Movement/eating handled by subclasses
        is_dead = self.age_and_check_death()
        offspring = None
        if not is_dead:
           offspring = self.try_reproduce(environment)

        return is_dead, offspring # Return death status and any new offspring

    # Placeholder methods for subclasses
    def eat(self, environment):
        pass

class Plant:
    """Represents a food resource."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.energy = PLANT_ENERGY
        self.symbol = '*'

    def __repr__(self):
        return self.symbol

class Herbivore(Organism):
    """Eats plants."""
    def __init__(self, x, y):
        super().__init__(x, y, HERBIVORE_MAX_ENERGY, HERBIVORE_MOVE_COST,
                         HERBIVORE_REPRODUCE_THRESHOLD, HERBIVORE_REPRODUCE_COST,
                         HERBIVORE_MAX_AGE, HERBIVORE_SIGHT_RANGE)
        self.symbol = 'H'

    def __repr__(self):
        return self.symbol

    def eat(self, environment):
        # Check current location first
        plant = environment.get_plant_at(self.x, self.y)
        if plant:
            self.energy = min(self.max_energy, self.energy + HERBIVORE_EAT_GAIN)
            environment.remove_plant(plant)
            return True # Ate successfully
        return False # Did not eat


    def _find_food(self, environment):
        """Scans nearby cells for plants."""
        for dx in range(-self.sight_range, self.sight_range + 1):
            for dy in range(-self.sight_range, self.sight_range + 1):
                if dx == 0 and dy == 0: continue
                nx, ny = self.x + dx, self.y + dy
                if self._is_valid_pos(nx, ny, environment.width, environment.height):
                    if environment.get_plant_at(nx, ny):
                        # Return direction towards food
                        return (1 if dx > 0 else -1 if dx < 0 else 0,
                                1 if dy > 0 else -1 if dy < 0 else 0)
        return None # No food found

    def move(self, environment):
        if self.energy <= self.move_cost:
            return

        target_dir = self._find_food(environment)

        if target_dir: # Move towards food if found
            dx, dy = target_dir
        else: # Random walk if no food nearby
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])

        new_x, new_y = self.x + dx, self.y + dy

        # Allow moving into a cell with a plant (will eat it) or an empty cell
        if self._is_valid_pos(new_x, new_y, environment.width, environment.height):
            target_organism = environment.get_organism_at(new_x, new_y)
            if target_organism is None: # Can move if empty or only contains a plant
                self.x = new_x
                self.y = new_y
                self.energy -= self.move_cost


    def update(self, environment):
        is_dead = self.age_and_check_death()
        offspring = None

        if not is_dead:
            # Order: Eat first, then move, then reproduce
            self.eat(environment)
            self.move(environment)
            # Re-check if position has changed to eat again (if moved onto plant)
            self.eat(environment)
            offspring = self.try_reproduce(environment)

        return is_dead, offspring


class Carnivore(Organism):
    """Eats Herbivores."""
    def __init__(self, x, y):
        super().__init__(x, y, CARNIVORE_MAX_ENERGY, CARNIVORE_MOVE_COST,
                         CARNIVORE_REPRODUCE_THRESHOLD, CARNIVORE_REPRODUCE_COST,
                         CARNIVORE_MAX_AGE, CARNIVORE_SIGHT_RANGE)
        self.symbol = 'C'

    def __repr__(self):
        return self.symbol

    def eat(self, environment):
        # Scan adjacent cells for herbivores
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                nx, ny = self.x + dx, self.y + dy
                if self._is_valid_pos(nx, ny, environment.width, environment.height):
                    target = environment.get_organism_at(nx, ny)
                    if isinstance(target, Herbivore):
                        self.energy = min(self.max_energy, self.energy + CARNIVORE_EAT_GAIN)
                        environment.remove_organism(target) # Remove the eaten herbivore
                        return True # Ate successfully
        return False # Did not eat

    def _find_prey(self, environment):
        """Scans nearby cells for herbivores."""
        for dx in range(-self.sight_range, self.sight_range + 1):
            for dy in range(-self.sight_range, self.sight_range + 1):
                if dx == 0 and dy == 0: continue
                nx, ny = self.x + dx, self.y + dy
                if self._is_valid_pos(nx, ny, environment.width, environment.height):
                    target = environment.get_organism_at(nx, ny)
                    if isinstance(target, Herbivore):
                         # Return direction towards prey
                        return (1 if dx > 0 else -1 if dx < 0 else 0,
                                1 if dy > 0 else -1 if dy < 0 else 0)
        return None # No prey found


    def move(self, environment):
        if self.energy <= self.move_cost:
            return

        target_dir = self._find_prey(environment)

        if target_dir: # Move towards prey if found
            dx, dy = target_dir
        else: # Random walk if no prey nearby
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])

        new_x, new_y = self.x + dx, self.y + dy

        # Allow moving only into empty cells (eating happens separately)
        if self._is_valid_pos(new_x, new_y, environment.width, environment.height):
             target_organism = environment.get_organism_at(new_x, new_y)
             target_plant = environment.get_plant_at(new_x, new_y)
             if target_organism is None and target_plant is None: # Move only if completely empty
                 self.x = new_x
                 self.y = new_y
                 self.energy -= self.move_cost


    def update(self, environment):
        is_dead = self.age_and_check_death()
        offspring = None

        if not is_dead:
             # Order: Try to eat adjacent prey first, then move, then reproduce
            self.eat(environment) # Checks adjacent cells
            self.move(environment)
            # Doesn't try eating again after move in this simple model
            offspring = self.try_reproduce(environment)

        return is_dead, offspring


class Environment:
    """Manages the grid, organisms, and resources."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.organisms = []
        self.plants = []
        # Optional: Use a grid for faster lookups, but lists are simpler for now
        # self.grid = [[None for _ in range(height)] for _ in range(width)]

    def add_organism(self, organism):
        if organism and self._is_valid_pos(organism.x, organism.y, self.width, self.height):
            self.organisms.append(organism)

    def remove_organism(self, organism):
        if organism in self.organisms:
            self.organisms.remove(organism)

    def add_plant(self, plant):
         if plant and self._is_valid_pos(plant.x, plant.y, self.width, self.height):
             # Prevent adding plant where an organism already is
             if self.get_organism_at(plant.x, plant.y) is None and self.get_plant_at(plant.x, plant.y) is None:
                 self.plants.append(plant)

    def remove_plant(self, plant):
        if plant in self.plants:
            self.plants.remove(plant)

    def get_organism_at(self, x, y):
        for org in self.organisms:
            if org.x == x and org.y == y:
                return org
        return None

    def get_plant_at(self, x, y):
        for plant in self.plants:
            if plant.x == x and plant.y == y:
                return plant
        return None

    def _is_valid_pos(self, x, y, width, height):
        return 0 <= x < width and 0 <= y < height

    def update_resources(self):
        # Plant regeneration
        for r in range(self.height):
            for c in range(self.width):
                if random.random() < PLANT_REGEN_RATE:
                    if self.get_organism_at(c, r) is None and self.get_plant_at(c, r) is None:
                        self.add_plant(Plant(c, r))

    def display(self, step):
        if CLEAR_SCREEN:
            os.system('cls' if os.name == 'nt' else 'clear')
        else:
            print("\n" * 5) # Add spacing if not clearing screen

        print(f"--- Ecosystem Simulation: Step {step} ---")
        # Create display grid
        display_grid = [['.' for _ in range(self.width)] for _ in range(self.height)]

        # Place plants
        for plant in self.plants:
            display_grid[plant.y][plant.x] = plant.symbol

        # Place organisms (organisms override plants in display)
        for org in self.organisms:
            display_grid[org.y][org.x] = org.symbol

        # Print grid
        print("+" + "-" * self.width + "+")
        for row in display_grid:
            print("|" + "".join(row) + "|")
        print("+" + "-" * self.width + "+")

        # Print stats
        herb_count = sum(1 for org in self.organisms if isinstance(org, Herbivore))
        carn_count = sum(1 for org in self.organisms if isinstance(org, Carnivore))
        plant_count = len(self.plants)
        print(f"Plants: {plant_count}, Herbivores: {herb_count}, Carnivores: {carn_count}")
        print("-" * (self.width + 2))


# --- Simulation ---

class Simulation:
    def __init__(self, width, height, num_plants, num_herbivores, num_carnivores):
        self.environment = Environment(width, height)
        self.populate_initial(num_plants, num_herbivores, num_carnivores)

    def get_random_empty_pos(self):
        attempts = 0
        while attempts < self.environment.width * self.environment.height:
            x = random.randint(0, self.environment.width - 1)
            y = random.randint(0, self.environment.height - 1)
            if self.environment.get_organism_at(x, y) is None and \
               self.environment.get_plant_at(x, y) is None:
                return x, y
            attempts += 1
        return None # No empty spot found

    def populate_initial(self, num_plants, num_herbivores, num_carnivores):
        # Add plants
        for _ in range(num_plants):
            pos = self.get_random_empty_pos()
            if pos:
                self.environment.add_plant(Plant(pos[0], pos[1]))

        # Add herbivores
        for _ in range(num_herbivores):
            pos = self.get_random_empty_pos()
            if pos:
                self.environment.add_organism(Herbivore(pos[0], pos[1]))

        # Add carnivores
        for _ in range(num_carnivores):
            pos = self.get_random_empty_pos()
            if pos:
                self.environment.add_organism(Carnivore(pos[0], pos[1]))


    def run(self, num_steps):
        for step in range(num_steps):
            # Display current state
            self.environment.display(step + 1)

            # Update resources (plant growth)
            self.environment.update_resources()

            # Update organisms
            newly_born = []
            died_this_step = []

            # Use copy to iterate safely while modifying the original list
            for org in copy.copy(self.environment.organisms):
                 if org in self.environment.organisms: # Check if it hasn't been eaten already this step
                    is_dead, offspring = org.update(self.environment)

                    if is_dead:
                        died_this_step.append(org)
                    if offspring:
                        newly_born.append(offspring)

            # Remove dead organisms after iterating
            for dead_org in died_this_step:
                 self.environment.remove_organism(dead_org)

            # Add newborns
            for baby in newly_born:
                self.environment.add_organism(baby) # add_organism handles placing it

            # Simple mechanism to prevent overpopulation explosion in one step
            # Could add carrying capacity limits here too

            # Pause for visualization
            time.sleep(FRAME_DELAY)

        print("\nSimulation finished.")


# --- Main Execution ---
if __name__ == "__main__":
    simulation = Simulation(GRID_WIDTH, GRID_HEIGHT,
                            INITIAL_PLANTS, INITIAL_HERBIVORES, INITIAL_CARNIVORES)
    simulation.run(NUM_STEPS)