import matplotlib.pyplot as plt
import numpy as np
from random import random

rot90 = np.array([[0,-1],[1,0]])

class Robot(object):
    def __init__(self, origin, angle, half_width=4, scan_range=20, view_dist=25, tick=0.5):
        self.origin = np.array(origin)
        self.angle = angle
        self.half_width = half_width
        self.scan_range = scan_range # ultrasonic
        self.view_dist = view_dist   # camera
        self.tick = tick

    def set_angle(self,angle):
        self.angle = angle

    def set_speed(self,speed):
        self.v = speed

    def set_itinerary(self, path):
        # the first point to visit is the last element in the list
        self.itinerary = list(reversed(path))

    def start_mission(self, world, speed=10):
        self.path = [self.origin.copy()]
        self.set_speed(speed)
        self.visited = []
        self.missed = []
        self.found_tags = []

        while len(self.itinerary) > 0:
            target = self.itinerary.pop()
            self.go(target,world)

        print 'Found %i tags:' %len(self.found_tags)
        return self.visited, self.missed

    def go(self, target, world):
        delta = self.v * self.tick
        self.angle = np.arctan2(*reversed(target - self.origin))
        dS = delta * np.array([np.cos(self.angle), np.sin(self.angle)])

        print 'target:', target,
        distance = np.linalg.norm(self.origin - target)
        while distance > delta:
            obs = world.closest_obstacle(self.origin, world.visible_obstacles(self.origin,
                                                                              self.scan_range,
                                                                              self.half_width,
                                                                              self.angle,
                                                                              distance))


            if not obs:
                tags = world.visible_tags(self.origin, self.view_dist, self.angle)
                #if len(tags) > 1:
                #    print 'SEEING MULTIPLE: ', tags
                new_tags = self.remember_tags(tags)
                closest_tags = sorted((np.linalg.norm(tag-self.origin), tag)
                                      for tag in new_tags)

                if len(closest_tags) > 0:
                    new_target = np.array(closest_tags[0][1])
                    print '- postponed. New tag found at:', new_target
                    self.itinerary.append(target)
                    self.itinerary.append(new_target)
                    return False
                self.origin += dS
                self.path.append(self.origin.copy())
                distance = np.linalg.norm(self.origin-target)
            else:
                ob_center,ob_radius = obs

                # target inside or close the obstacle
                if np.linalg.norm(ob_center-target) < ob_radius + 3*self.half_width:
                    print '- missed'
                    if len(self.itinerary) > 0:
                        if np.linalg.norm(self.itinerary[-1]-target) > 5*self.half_width:
                            new_target = np.add(0.7*target, 0.3*self.itinerary[-1])
                            print 'new intermediate target added:',new_target
                            self.itinerary.append(new_target)
                    return False
                else:
                    ob_direction = ob_center-self.origin
                    if np.cross(dS, ob_direction) > 0: # obstacle is on the left
                        ort = rot90.dot(-dS)/np.linalg.norm(dS)
                    else:
                        ort = rot90.dot(dS)/np.linalg.norm(dS)

                    new_target = ob_center + ort * (ob_radius + 2*self.half_width)
                    print '- postponed. Go round the obstacle to:',new_target
                    self.itinerary.append(target)
                    self.itinerary.append(new_target)
                    return False

        print 'reached'
        return True

    def remember_tags(self, tags):
        new_tags = []
        for tag in tags:
            if tag not in self.found_tags:
                new_tags.append(tag)
        self.found_tags += new_tags
        return new_tags


def spiral(turns=5,origin=(0.,0.),step=15.):
    xy = np.array(origin,dtype='float32')
    R = np.array([[0.,-1.], [1., 0.]])
    L = step
    vec = np.array([0,1])
    mission = []
    for i in range(2*turns):
        xy += L * vec
        mission.append(xy.copy())
        vec = R.dot(vec)
        xy += L * vec
        mission.append(xy.copy())
        vec = R.dot(vec)
        L += step
    return mission


class World(object):
    def __init__(self,obstacles=4,tags=10,distance=10):
        self.obstacles = []
        while len(self.obstacles) < obstacles:
            new_ob = np.array( (250*(random()-0.5),250*(random()-0.5),10+15*random() ) )
            if all([ np.linalg.norm(new_ob[:2]-ob[:2]) > new_ob[2]+ob[2]+distance for ob in self.obstacles]):
                self.obstacles.append(new_ob)

        self.tags = []
        while len(self.tags) < tags:
            new_tag = np.array( (250*(random()-0.5),250*(random()-0.5),random()>0.9 ) )
            if all([ np.linalg.norm(new_tag[:2]-ob[:2]) > ob[2] for ob in self.obstacles ]):
                self.tags.append(new_tag)
        print "%i obstacles and %i tags generated:\n" %(obstacles,tags), self.tags

    def visible_obstacles(self, origin, scan_range, half_width, angle, distance):
        xy = origin + scan_range * np.array([np.cos(angle), np.sin(angle)])
        for ob in self.obstacles:
            if np.linalg.norm(xy-ob[:2]) < ob[2]+half_width/2 and distance > np.linalg.norm(origin-ob[:2])-ob[2]:
                yield ob

    def closest_obstacle(self, origin, obstacles):
        closest = [(np.linalg.norm(origin-ob[:2])-ob[2], ob[:2], ob[2]) for ob in obstacles]
        if not closest:
            return None
        _, ob_center, ob_radius = min(closest)
        return ob_center, ob_radius

    def visible_tags(self, origin, view_dist, angle):
        xy = origin + view_dist * np.array([np.cos(angle), np.sin(angle)])
        return [ tuple(tag[:2]) for tag in self.tags if np.linalg.norm(tag[:2]-xy) < view_dist/2 ]




def main():
    robot = Robot((0.,0.),0.77)
    world = World(obstacles=5,tags=25)

    mission = spiral(turns=6,origin=(0.,0.),step=20)
    mission.append(np.array([0.,0.]))

    robot.set_itinerary(mission)
    visited,missed = robot.start_mission(world)

    print 'missed points:',missed

    #plt.ion()
    #plt.clf()
    fig = plt.figure()
    Ox,Oy,_ = zip(*world.obstacles)
    circs = [ plt.Circle(tuple(ob[:2]),ob[2],color='r') for ob in world.obstacles ]
    for circ in circs:
        fig.gca().add_artist(circ)
    Tx,Ty,_ = zip(*world.tags)
    X,Y = zip(*robot.path)
    plt.plot(Tx,Ty,'g^',Ox,Oy,'ro',X,Y,'b-')
    #plt.draw()
    plt.show()
