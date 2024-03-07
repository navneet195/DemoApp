//
//  StringHelper.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation
public extension String {
    static var empty: String {
        ""
    }
    var isNumeric: Bool {
        return self.allSatisfy { $0.isNumber }
    }
}
