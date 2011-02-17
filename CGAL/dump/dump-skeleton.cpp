#include<string>
#include<iostream>
#include<vector>

#include<boost/shared_ptr.hpp>

#include<CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include<CGAL/Polygon_with_holes_2.h>
#include<CGAL/create_straight_skeleton_from_polygon_with_holes_2.h>

#include "print.h"

typedef CGAL::Exact_predicates_inexact_constructions_kernel K ;

typedef K::Point_2                   Point ;
typedef CGAL::Polygon_2<K>           Polygon ;
typedef CGAL::Polygon_with_holes_2<K> Polygon_with_holes;
typedef CGAL::Straight_skeleton_2<K> Ss ;

typedef boost::shared_ptr<Ss> SsPtr ;

int main()
{
  Polygon outer;
  std::vector<Polygon *> inners;

  std::string line;
  double x, y;
  Polygon *current = &outer;

  while (!getline(std::cin,line).eof()) {
    std::istringstream is(line);
    if (line == "") {
	current = new Polygon();
	inners.push_back(current);
	continue;
    }
    if (!(is >> x >> y)) {
        std::cerr << "Bad input line: " << line;
        continue;
    }
    current->push_back(Point(x, y));
  }

  Polygon_with_holes poly(outer);
  for (std::vector<Polygon *>::iterator it = inners.begin(); it != inners.end(); it++)
    poly.add_hole(**it);

  SsPtr iss = CGAL::create_interior_straight_skeleton_2(poly);
  print_skeleton_inner_bisectors(*iss);
  return 0;
}
