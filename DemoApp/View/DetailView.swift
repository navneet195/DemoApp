//
//  DetailView.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import SwiftUI

struct DetailView: View {

    @EnvironmentObject var viewmodel: UserProfileViewModel
    var userModel: UserModel
    @State var newCompanyName = String.empty

    var body: some View {
        VStack(alignment: .leading) {
            Text("\(DetailViewConstants.currentCompanyName) \(userModel.name)")
            TextField(DetailViewConstants.enterComapnyName, text: $newCompanyName)
                .padding()
                .overlay(RoundedRectangle(cornerRadius: 10.0).strokeBorder(Color.black, style: StrokeStyle(lineWidth: 1.0)))
                .padding()
            Button(DetailViewConstants.doneButton) {
                viewmodel.trigger(by: .updateCompanyName(name: newCompanyName, currentModel: userModel))
            }
        }
        .padding()
    }
}

