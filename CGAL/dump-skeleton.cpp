#include<string>
#include<iostream>

#include<boost/shared_ptr.hpp>

#include<CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include<CGAL/Polygon_2.h>
#include<CGAL/create_straight_skeleton_2.h>

#include "print.h"

typedef CGAL::Exact_predicates_inexact_constructions_kernel K ;

typedef K::Point_2                   Point ;
typedef CGAL::Polygon_2<K>           Polygon ;
typedef CGAL::Polygon_with_holes_2<K> Polygon_with_holes;
typedef CGAL::Straight_skeleton_2<K> Ss ;

typedef boost::shared_ptr<Ss> SsPtr ;

int main()
{
  Polygon outer ;
  
  /*
  poly.push_back( Point(-1,-1) ) ;
  poly.push_back( Point(0,-12) ) ;
  poly.push_back( Point(1,-1) ) ;
  poly.push_back( Point(12,0) ) ;
  poly.push_back( Point(1,1) ) ;
  poly.push_back( Point(0,12) ) ;
  poly.push_back( Point(-1,1) ) ;
  poly.push_back( Point(-12,0) ) ;
  */
  std::string line;
  double x, y;
  while (!getline(std::cin,line).eof()) {
    std::istringstream is(line);
    if (!(is >> x >> y)) {
        std::cerr << "Bad input line: " << line;
        continue;
    }
    outer.push_back(Point(x, y));
  }

  // You can pass the polygon via an iterator pair
  //Polygon_with_holes poly(outer);
  SsPtr iss = CGAL::create_interior_straight_skeleton_2(outer);

  // Or you can pass the polygon directly, as below.
  
  // To create an exterior straight skeleton you need to specify a maximum offset.
  // double lMaxOffset = 5 ; 
  // SsPtr oss = CGAL::create_exterior_straight_skeleton_2(lMaxOffset, poly);
  
  print_skeleton_inner_bisectors(*iss);
  // print_straight_skeleton(*oss);
  
  return 0;
}
